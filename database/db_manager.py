import os
import re
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class PlateRecord(Base):
    __tablename__ = 'plates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    number_text = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    image_path = Column(Text, nullable=True)
    full_image_path = Column(Text, nullable=True)
    source_type = Column(String(20))
    source_path = Column(Text, nullable=True)

class SystemLog(Base):
    __tablename__ = 'system_logs'
    id = Column(Integer, primary_key=True)
    event_type = Column(String)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.now)

class Watchlist(Base):
    __tablename__ = 'watchlist'
    id = Column(Integer, primary_key=True)
    number_text = Column(String, unique=True, nullable=False)
    added_at = Column(DateTime, default=datetime.now)

class Vehicle(Base):
    __tablename__ = 'vehicles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    plate_number = Column(String(50), unique=True, nullable=False)
    owner_name = Column(String(100))
    owner_contact = Column(String(20))
    owner_address = Column(Text)
    make = Column(String(50))
    model = Column(String(50))
    year = Column(Integer)
    color = Column(String(30))
    engine_number = Column(String(50))
    chassis_number = Column(String(50))
    registration_date = Column(DateTime)
    expiry_date = Column(DateTime)
    status = Column(String(20), default="Registered") # Registered, Stolen, Expired, etc.
    notes = Column(Text)

class DatabaseManager:
    def __init__(self, db_path='npds_data.db'):
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_plate(self, number, confidence, image_path, full_image_path, source_type, source_path):
        session = self.Session()
        try:
            # Normalize ONLY for comparison (deduplication)
            clean_number = re.sub(r'[^A-Z0-9]', '', number.upper())
            
            # Check for existing record of this plate (insensitive to spaces) within last 24 hours
            limit = datetime.now() - timedelta(hours=24)
            
            # We fetch recent records and compare normalized versions in-memory 
            # OR use a more complex SQL query. For SQLite, in-memory is fine for "recent" records.
            recent_records = session.query(PlateRecord).filter(
                PlateRecord.timestamp >= limit
            ).order_by(PlateRecord.timestamp.desc()).all()
            
            existing = None
            for rec in recent_records:
                if re.sub(r'[^A-Z0-9]', '', rec.number_text.upper()) == clean_number:
                    existing = rec
                    break
            
            if existing:
                # Update existing record
                existing.timestamp = datetime.now()
                existing.confidence = max(existing.confidence, confidence)
                # Keep original number_text or update it? Let's keep the one that looks better (usually longer)
                if len(number) > len(existing.number_text):
                    existing.number_text = number
                    
                if image_path: existing.image_path = image_path
                if full_image_path: existing.full_image_path = full_image_path
                session.commit()
                return existing.id
            else:
                # Create a new record with ORIGINAL formatting
                record = PlateRecord(
                    number_text=number,
                    confidence=confidence,
                    image_path=image_path,
                    full_image_path=full_image_path,
                    source_type=source_type,
                    source_path=source_path,
                    timestamp=datetime.now()
                )
                session.add(record)
                session.commit()
                return record.id
        except Exception as e:
            session.rollback()
            print(f"Error adding plate: {e}")
            return None
        finally:
            session.close()

    def get_recent_plates(self, limit=10):
        session = self.Session()
        try:
            results = session.query(PlateRecord).order_by(PlateRecord.timestamp.desc()).limit(limit).all()
            return results
        finally:
            session.close()

    def get_stats(self):
        """Returns tuple: (total_detections, detections_today)"""
        session = self.Session()
        try:
            total = session.query(PlateRecord).count()
            
            # Count today
            start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_count = session.query(PlateRecord).filter(PlateRecord.timestamp >= start_of_day).count()
            
            return total, today_count
        finally:
            session.close()

    def clear_all_records(self):
        session = self.Session()
        try:
            session.query(PlateRecord).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error clearing db: {e}")
        finally:
            session.close()

    # --- Watchlist Methods ---
    def add_to_watchlist(self, number_text):
        session = self.Session()
        try:
            exists = session.query(Watchlist).filter_by(number_text=number_text).first()
            if not exists:
                item = Watchlist(number_text=number_text)
                session.add(item)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            print(f"Error adding to watchlist: {e}")
            return False
        finally:
            session.close()

    def remove_from_watchlist(self, number_text):
        session = self.Session()
        try:
            session.query(Watchlist).filter_by(number_text=number_text).delete()
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error removing from watchlist: {e}")
        finally:
            session.close()

    def get_watchlist(self):
        session = self.Session()
        try:
            return [item.number_text for item in session.query(Watchlist).all()]
        finally:
            session.close()

    # --- Analytics Methods ---
    def get_daily_stats(self, start_date, end_date):
        """Returns list of (date_str, count)"""
        session = self.Session()
        try:
            query = session.query(
                func.date(PlateRecord.timestamp), func.count(PlateRecord.id)
            ).filter(
                PlateRecord.timestamp >= start_date, 
                PlateRecord.timestamp <= end_date
            ).group_by(
                func.date(PlateRecord.timestamp)
            ).all()
            
            return query
        except Exception as e:
            print(f"Stats Error: {e}")
            return []
        finally:
            session.close()

    def get_all_records(self):
        session = self.Session()
        try:
            return session.query(PlateRecord).order_by(PlateRecord.timestamp.desc()).all()
        finally:
            session.close()

    # --- Vehicle Methods ---
    def add_vehicle(self, data):
        session = self.Session()
        try:
            # Check if exists
            exists = session.query(Vehicle).filter_by(plate_number=data.get('plate_number')).first()
            if exists:
                for key, value in data.items():
                    setattr(exists, key, value)
            else:
                vehicle = Vehicle(**data)
                session.add(vehicle)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error adding vehicle: {e}")
            return False
        finally:
            session.close()

    def get_vehicle(self, plate_number):
        session = self.Session()
        try:
            # Space-insensitive lookup: Normalize search term
            search_clean = re.sub(r'[^A-Z0-9]', '', plate_number.upper())
            
            # Fetch all vehicles and compare in-memory (best for SQLite without complex extensions)
            all_v = session.query(Vehicle).all()
            for v in all_v:
                if re.sub(r'[^A-Z0-9]', '', v.plate_number.upper()) == search_clean:
                    return v
            return None
        finally:
            session.close()

    def get_all_vehicles(self):
        session = self.Session()
        try:
            return session.query(Vehicle).all()
        finally:
            session.close()

    def delete_vehicle(self, plate_number):
        session = self.Session()
        try:
            session.query(Vehicle).filter_by(plate_number=plate_number).delete()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Error deleting vehicle: {e}")
            return False
        finally:
            session.close()

    def log_event(self, event_type, message):
        session = self.Session()
        try:
            log = SystemLog(event_type=event_type, message=message)
            session.add(log)
            session.commit()
        except Exception as e:
            print(f"Logging error: {e}")
        finally:
            session.close()
