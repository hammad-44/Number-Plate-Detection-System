from PyQt5.QtCore import Qt, pyqtSignal, QRegExp
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem, QHeaderView, QLabel
from PyQt5.QtGui import QIntValidator, QRegExpValidator
import re

from qfluentwidgets import (TableWidget, PrimaryPushButton, SearchLineEdit, 
                            StrongBodyLabel, CardWidget, FluentIcon as FIF,
                            MessageBox, LineEdit, BodyLabel, SubtitleLabel,
                            Dialog, MessageBoxBase, InfoBar, InfoBarPosition,
                            ComboBox, ToolButton, TransparentToolButton, CaptionLabel,
                            SingleDirectionScrollArea, InfoBadge)


class VehicleInfoDialog(MessageBoxBase):
    """ Read-only dialog to display detected vehicle information """
    def __init__(self, parent, vehicle, plate_text):
        super().__init__(parent)
        self.setWindowTitle("Vehicle Detection Details")
        
        self.content_layout = self.viewLayout
        
        # Title with plate number
        self.title_label = SubtitleLabel(f"Detection: {plate_text}", self)
        self.title_label.setStyleSheet("color: #0078d4; font-weight: bold; font-size: 24px;")
        self.content_layout.addWidget(self.title_label)
        
        # Status Badge
        status = vehicle.status if vehicle else "Not in Database"
        self.status_badge = InfoBadge.info(status)
        if vehicle:
            if vehicle.status == "Registered":
                self.status_badge.setCustomBackgroundColor("#28a745", "#28a745")
            elif vehicle.status == "Stolen":
                self.status_badge.setCustomBackgroundColor("#dc3545", "#dc3545")
        else:
            self.status_badge.setCustomBackgroundColor("#ffc107", "#ffc107")
            
        badge_container = QHBoxLayout()
        badge_container.addWidget(self.status_badge)
        badge_container.addStretch()
        self.content_layout.addLayout(badge_container)
        
        # Details Grid
        details_layout = QVBoxLayout()
        details_layout.setSpacing(10)
        details_layout.setContentsMargins(0, 15, 0, 15)
        
        def add_detail(label, value, icon):
            row = QHBoxLayout()
            icon_lbl = QLabel() # Placeholder or use FIF if possible
            row.addWidget(BodyLabel(f"<b>{label}:</b> {value or '-'}"))
            details_layout.addLayout(row)

        if vehicle:
            add_detail("Owner Name", vehicle.owner_name, FIF.PEOPLE)
            add_detail("Contact", vehicle.owner_contact, FIF.PHONE)
            add_detail("Vehicle", f"{vehicle.make} {vehicle.model} ({vehicle.color})", FIF.CAR)
            add_detail("Engine #", vehicle.engine_number, FIF.FINGERPRINT)
            add_detail("Chassis #", vehicle.chassis_number, FIF.FINGERPRINT)
            add_detail("Year", vehicle.year, FIF.CALENDAR)
        else:
            msg = BodyLabel("This vehicle is not registered in the system.")
            msg.setStyleSheet("color: #808080; font-style: italic;")
            details_layout.addWidget(msg)
            
        self.content_layout.addLayout(details_layout)
        
        self.yesButton.setText("Close")
        self.cancelButton.hide()
        self.widget.setMinimumWidth(400)

class AddVehicleDialog(MessageBoxBase):
    """ Custom dialog to add/edit vehicle details """
    def __init__(self, parent=None, vehicle_data=None):
        super().__init__(parent)
        self.setWindowTitle("Vehicle Details")
        
        self.content_layout = self.viewLayout
        self.title_label = SubtitleLabel("Enter Vehicle Information", self)
        self.content_layout.addWidget(self.title_label)
        
        # Form State
        self.fields = {}
        self.error_labels = {}
        
        # Scroll Area for long content
        self.scroll_area = SingleDirectionScrollArea(self.widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 5, 15, 5)
        self.scroll_layout.setSpacing(15)
        
        # Section: Vehicle Information
        self.scroll_layout.addWidget(BodyLabel("Vehicle Details"))
        self.add_field("plate_number", "Plate Number (e.g. ABC 1234)", FIF.CARE_RIGHT_SOLID)
        self.add_field("make", "Make (e.g. Toyota)", FIF.CAR)
        self.add_field("model", "Model (e.g. Corolla)", FIF.CAR)
        self.add_field("year", "Year (1900-2100)", FIF.CALENDAR)
        self.add_field("color", "Color", FIF.PALETTE)
        self.add_field("engine_number", "Engine Number", FIF.FINGERPRINT)
        self.add_field("chassis_number", "Chassis Number", FIF.FINGERPRINT)
        self.add_field("status", "Status", FIF.INFO)

        self.scroll_layout.addSpacing(10)
        
        # Section: Owner Information
        self.scroll_layout.addWidget(BodyLabel("Owner Details"))
        self.add_field("owner_name", "Owner Name", FIF.PEOPLE)
        self.add_field("owner_contact", "Owner Contact", FIF.PHONE)

        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setFixedHeight(450)
        self.content_layout.addWidget(self.scroll_area)
        
        if vehicle_data:
            for key, val in vehicle_data.items():
                if key in self.fields:
                    widget = self.fields[key]
                    if isinstance(widget, ComboBox):
                        widget.setCurrentText(str(val))
                    else:
                        widget.setText(str(val))
                    
        self.yesButton.setText("Save")
        self.cancelButton.setText("Cancel")
        self.widget.setMinimumWidth(450)
        
        # Initial validity check
        self.update_save_button()

    def add_field(self, key, placeholder, icon):
        container = QVBoxLayout()
        container.setSpacing(2)
        
        if key == "status":
            edit = ComboBox(self)
            edit.addItems(["Registered", "Stolen", "Expired", "Suspended"])
            edit.setCurrentIndex(0)
        else:
            edit = LineEdit(self)
            edit.setPlaceholderText(placeholder)
            edit.setClearButtonEnabled(True)
            
            # Apply Strict Validators
            if key == "year":
                edit.setValidator(QIntValidator(1900, 2100, self))
            elif key == "plate_number":
                reg = QRegExp(r'^[A-Z0-9\-\s]+$')
                edit.setValidator(QRegExpValidator(reg, self))
            elif key in ["engine_number", "chassis_number"]:
                reg = QRegExp(r'^[A-Z0-9]+$')
                edit.setValidator(QRegExpValidator(reg, self))
            elif key == "owner_contact":
                reg = QRegExp(r'^[0-9+]+$')
                edit.setValidator(QRegExpValidator(reg, self))
            
            edit.textChanged.connect(lambda t, k=key: self.on_text_changed(k, t))

        self.fields[key] = edit
        container.addWidget(edit)
        
        error_lbl = CaptionLabel("", self)
        error_lbl.setStyleSheet("color: #ff4d4f; font-size: 11px;")
        error_lbl.hide()
        self.error_labels[key] = error_lbl
        container.addWidget(error_lbl)
        
        self.scroll_layout.addLayout(container)

    def get_data(self):
        data = {}
        for key, widget in self.fields.items():
            if isinstance(widget, ComboBox):
                data[key] = widget.currentText()
            else:
                data[key] = widget.text().strip()
        return data

    def validate(self):
        data = self.get_data()
        
        # Strip spaces/hyphens for final database format check
        norm_plate = re.sub(r'[^A-Z0-9]', '', data['plate_number']).upper()
        if not re.match(r'^[A-Z]{1,4}\d{1,5}$', norm_plate):
            return False, "Invalid Plate Format! Example: ABC 1234 or LE-123"
            
        if data['owner_contact'] and not re.match(r'^(\+92|0)3\d{9}$', data['owner_contact'].replace("-","")):
             return False, "Invalid Contact Number! Format: 03001234567 or +923001234567"
             
        if not data['owner_name']:
            return False, "Owner name is required!"
            
        return True, ""

    def on_text_changed(self, key, text):
        """ Real-time validation handler """
        is_valid, msg = self.validate_field(key, text)
        
        widget = self.fields[key]
        label = self.error_labels[key]
        
        if not is_valid and text:
            widget.setStyleSheet("border: 1px solid #ff4d4f;")
            label.setText(msg)
            label.show()
        else:
            widget.setStyleSheet("")
            label.hide()
            
        self.update_save_button()

    def update_save_button(self):
        """ Enable/Disable save button based on whole form validity """
        valid, _ = self.validate()
        self.yesButton.setEnabled(valid)

    def validate_field(self, key, text):
        if not text:
            return True, ""
            
        if key == "plate_number":
            # Allow spaces and hyphens for UI display and typing
            # Regex: 2-3 Letters, optional space/hyphen, then digits
            if not re.match(r'^[A-Z]{2,3}[\s\-]?\d{1,4}$', text, re.IGNORECASE):
                return False, "Format: ABC 1234 or LE123"
        elif key == "owner_contact":
            if not re.match(r'^(\+92|0)3\d{9}$', text.replace("-","")):
                return False, "Format: 03001234567 or +923001234567"
        elif key == "year":
            try:
                if not (1900 <= int(text) <= 2100):
                    return False, "Year 1900-2100"
            except:
                return False, "Invalid Year"
                
        return True, ""

class VehiclesInterface(QWidget):
    def __init__(self, db_manager):
        super().__init__()
        self.db = db_manager
        self.setObjectName('vehiclesInterface')
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.v_layout = QVBoxLayout(self)
        self.v_layout.setContentsMargins(30, 30, 30, 30)
        self.v_layout.setSpacing(20)

        # Header Row
        header_layout = QHBoxLayout()
        self.title = StrongBodyLabel("Vehicle Database", self)
        self.title.setStyleSheet("font-size: 24px;")
        
        self.search_input = SearchLineEdit(self)
        self.search_input.setPlaceholderText("Search Plate Number...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self.filter_table)
        
        self.add_btn = PrimaryPushButton("Add Vehicle", self, FIF.ADD)
        self.add_btn.clicked.connect(self.show_add_dialog)
        
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        header_layout.addWidget(self.search_input)
        header_layout.addWidget(self.add_btn)
        
        self.v_layout.addLayout(header_layout)

        # Table Card
        self.table_card = CardWidget(self)
        table_layout = QVBoxLayout(self.table_card)
        
        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Plate Number", "Owner", "Make/Model", "Color", "Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().hide()
        
        table_layout.addWidget(self.table)
        self.v_layout.addWidget(self.table_card)

    def load_data(self):
        vehicles = self.db.get_all_vehicles()
        self.table.setRowCount(0)
        for v in vehicles:
            self.add_table_row(v)

    def add_table_row(self, v):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(v.plate_number))
        self.table.setItem(row, 1, QTableWidgetItem(v.owner_name or "-"))
        self.table.setItem(row, 2, QTableWidgetItem(f"{v.make} {v.model}" if v.make else "-"))
        self.table.setItem(row, 3, QTableWidgetItem(v.color or "-"))
        
        status_item = QTableWidgetItem(v.status or "Registered")
        if v.status == "Stolen":
             status_item.setForeground(Qt.red)
        self.table.setItem(row, 4, status_item)
        
        # Actions Cell
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(4, 4, 4, 4)
        actions_layout.setSpacing(8)
        
        edit_btn = TransparentToolButton(FIF.EDIT, actions_widget)
        delete_btn = TransparentToolButton(FIF.DELETE, actions_widget)
        
        edit_btn.clicked.connect(lambda: self.edit_vehicle(v.plate_number))
        delete_btn.clicked.connect(lambda: self.delete_vehicle(v.plate_number))
        
        actions_layout.addWidget(edit_btn)
        actions_layout.addWidget(delete_btn)
        actions_layout.addStretch()
        
        self.table.setCellWidget(row, 5, actions_widget)

    def edit_vehicle(self, plate):
        vehicle = self.db.get_vehicle(plate)
        if not vehicle: return
        
        # Convert model to dict for dialog
        v_data = {
            'plate_number': vehicle.plate_number,
            'owner_name': vehicle.owner_name,
            'owner_contact': vehicle.owner_contact,
            'make': vehicle.make,
            'model': vehicle.model,
            'color': vehicle.color,
            'engine_number': vehicle.engine_number,
            'chassis_number': vehicle.chassis_number,
            'status': vehicle.status
        }
        
        w = AddVehicleDialog(self, vehicle_data=v_data)
        if w.exec():
            data = w.get_data()
            if self.db.add_vehicle(data):
                self.load_data()
                self.show_message("Updated", f"Vehicle {plate} updated successfully.")

    def delete_vehicle(self, plate):
        title = "Delete Vehicle"
        content = f"Are you sure you want to delete vehicle {plate}?"
        w = MessageBox(title, content, self)
        if w.exec():
            if self.db.delete_vehicle(plate):
                self.load_data()
                self.show_message("Deleted", f"Vehicle {plate} removed from database.")

    def filter_table(self, text):
        for i in range(self.table.rowCount()):
            plate = self.table.item(i, 0).text().lower()
            self.table.setRowHidden(i, text.lower() not in plate)

    def show_add_dialog(self):
        w = AddVehicleDialog(self)
        if w.exec():
            valid, error_msg = w.validate()
            if not valid:
                self.show_message("Validation Error", error_msg, is_error=True)
                return
                
            data = w.get_data()
            plate = data.get('plate_number')
            
            # Optional: Check if already exists to show a distinct message
            existing = self.db.get_vehicle(plate)
            
            if self.db.add_vehicle(data):
                self.load_data()
                msg = f"Vehicle {plate} updated successfully." if existing else f"Vehicle {plate} added successfully."
                self.show_message("Success", msg)
            else:
                self.show_message("Error", "Failed to save vehicle data.", is_error=True)

    def show_message(self, title, content, is_error=False):
        if is_error:
            InfoBar.error(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        else:
            InfoBar.success(
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
