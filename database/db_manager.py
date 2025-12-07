import os
from datetime import datetime
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

class DatabaseManager:
    def __init__(self, db_path='npds_data.db'):
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_plate(self, number, confidence, image_path, full_image_path, source_type, source_path):
        session = self.Session()
        try:
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
