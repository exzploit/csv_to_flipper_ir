import sys
import os
import glob
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QPlainTextEdit,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QComboBox, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject, QSettings
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor

# --- Dark Theme Stylesheet ---
FLIPPER_THEME = """
QMainWindow {
    background-color: #2b2b2b;
}
QWidget {
    color: #ffffff;
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    font-size: 14px;
}
QGroupBox {
    border: 1px solid #555;
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 10px;
    font-weight: bold;
    color: #e88004; /* Flipper Orange */
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
    background-color: #2b2b2b; 
}
QLineEdit, QComboBox {
    background-color: #3b3b3b;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 6px;
    color: #eee;
    selection-background-color: #e88004;
}
QTableWidget {
    background-color: #1e1e1e;
    alternate-background-color: #2a2a2a;
    gridline-color: #444;
    border: 1px solid #444;
    color: #eee;
    selection-background-color: #e88004;
    selection-color: #000;
}
QHeaderView::section {
    background-color: #333;
    color: #e88004;
    padding: 4px;
    border: 1px solid #444;
    font-weight: bold;
}
"""

class IRProtocolConverter:
    """Handles logic for various IR protocols."""
    
    @staticmethod
    def convert(protocol, device, subdevice, function):
        try:
            p = str(protocol).upper()
            d = int(device)
            s = int(subdevice)
            f = int(function)

            if p == "NEC":
                # NEC: address is dev(8bit) + sub(8bit), command is func(8bit) + ~func(8bit)
                addr_hex = f"{d:02X} {s:02X} 00 00"
                cmd_hex = f"{f:02X} {(~f & 0xFF):02X} 00 00"
                return addr_hex, cmd_hex
            
            elif p == "SAMSUNG":
                addr_hex = f"{d:02X} {s:02X} 00 00"
                cmd_hex = f"{f:02X} 00 00 00"
                return addr_hex, cmd_hex
            
            elif p == "SONY":
                addr_hex = f"{d:02X} 00 00 00"
                cmd_hex = f"{f:02X} 00 00 00"
                return addr_hex, cmd_hex
            
            elif p in ["RC5", "RC6"]:
                addr_hex = f"{d:02X} 00 00 00"
                cmd_hex = f"{f:02X} 00 00 00"
                return addr_hex, cmd_hex
            
            else:
                # Fallback for others (HEX)
                addr_hex = f"{d:04X} {s:04X}" if s != 0 else f"{d:04X} 00 00"
                cmd_hex = f"{f:04X} 00 00"
                return addr_hex, cmd_hex
        except:
            return "00 00 00 00", "00 00 00 00"

class IRConverterWorker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, input_dir, output_dir, group_by_csv=False):
        super().__init__()
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.group_by_csv = group_by_csv
        self.is_cancelled = False

    def stop(self):
        self.is_cancelled = True

    def run(self):
        csv_files = glob.glob(os.path.join(self.input_dir, "*.csv"))
        if not csv_files:
            self.error.emit("No CSV files found in the input folder.")
            self.finished.emit()
            return

        try:
            for i, csv_file in enumerate(csv_files):
                if self.is_cancelled:
                    self.log.emit("!! Process cancelled by user.")
                    break

                filename = os.path.basename(csv_file)
                self.log.emit(f"> Reading: {filename}...")
                
                try:
                    df = pd.read_csv(csv_file)
                except Exception as e:
                    self.log.emit(f"! Error reading {filename}: {e}")
                    continue

                required_cols = ['functionname', 'protocol', 'device', 'subdevice', 'function']
                if not all(col in df.columns for col in required_cols):
                    self.log.emit(f"! Skipping {filename}: Missing required columns.")
                    continue

                if self.group_by_csv:
                    remote_name = os.path.splitext(filename)[0]
                    remote_content = "Filetype: IR signals file\nVersion: 1\n"
                    
                    for _, row in df.iterrows():
                        func_name = str(row['functionname']).strip().replace('/', '_').replace('\\', '_')
                        protocol = str(row['protocol'])
                        addr, cmd = IRProtocolConverter.convert(protocol, row['device'], row['subdevice'], row['function'])
                        
                        remote_content += (
                            f"# \nname: {func_name}\n"
                            "type: parsed\n"
                            f"protocol: {protocol}\n"
                            f"address: {addr}\n"
                            f"command: {cmd}\n"
                        )
                    
                    file_path = os.path.join(self.output_dir, f"{remote_name}.ir")
                    with open(file_path, 'w') as f:
                        f.write(remote_content)
                else:
                    for _, row in df.iterrows():
                        func_name = str(row['functionname']).strip().replace('/', '_').replace('\\', '_')
                        protocol = str(row['protocol'])
                        addr, cmd = IRProtocolConverter.convert(protocol, row['device'], row['subdevice'], row['function'])
                        
                        ir_content = (
                            "Filetype: IR signals file\n"
                            "Version: 1\n"
                            f"name: {func_name}\n"
                            "type: parsed\n"
                            f"protocol: {protocol}\n"
                            f"address: {addr}\n"
                            f"command: {cmd}\n"
                        )

                        file_path = os.path.join(self.output_dir, f"{func_name}.ir")
                        with open(file_path, 'w') as f:
                            f.write(ir_content)
                
                self.log.emit(f"✓ Processed {filename}")
                self.progress.emit(i + 1)

            self.finished.emit()
        except Exception as e:
            self.error.emit(f"Fatal Error: {str(e)}")
            self.finished.emit()

class IRConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flipper Zero IR Converter")
        self.resize(1100, 850)
        self.setAcceptDrops(True)
        
        self.settings = QSettings("Exzploit", "FlipperIRConverter")
        self.current_csv_df = None
        
        # Apply Dark Theme
        self.setStyleSheet(FLIPPER_THEME)
        
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # --- Header ---
        header_layout = QVBoxLayout()
        title = QLabel("FLIPPER IR CONVERTER")
        title.setObjectName("HeaderLabel")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #e88004;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title)
        main_layout.addLayout(header_layout)

        # --- Configuration Group ---
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Input/Output rows
        for label_text, attr_name, placeholder, browse_func in [
            ("Input:", "input_entry", "Select Input Folder...", self.browse_input),
            ("Output:", "output_entry", "Select Output Folder...", self.browse_output)
        ]:
            row = QHBoxLayout()
            row.addWidget(QLabel(label_text))
            setattr(self, attr_name, QLineEdit())
            entry = getattr(self, attr_name)
            entry.setPlaceholderText(placeholder)
            entry.textChanged.connect(self.scan_for_csvs)
            btn = QPushButton("Browse...")
            btn.clicked.connect(browse_func)
            row.addWidget(entry)
            row.addWidget(btn)
            config_layout.addLayout(row)

        self.group_checkbox = QCheckBox("Group signals into a single .ir remote file")
        config_layout.addWidget(self.group_checkbox)
        main_layout.addWidget(config_group)

        # --- Preview Splitter ---
        preview_group = QGroupBox("Visual IR Previewer")
        preview_layout = QVBoxLayout(preview_group)
        
        file_selector_layout = QHBoxLayout()
        file_selector_layout.addWidget(QLabel("Preview File:"))
        self.file_combo = QComboBox()
        self.file_combo.currentIndexChanged.connect(self.load_selected_csv)
        file_selector_layout.addWidget(self.file_combo, 1)
        preview_layout.addLayout(file_selector_layout)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['Name', 'Protocol', 'Dev', 'Sub', 'Func'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.update_ir_preview)
        splitter.addWidget(self.table)
        
        # Preview Box
        self.preview_box = QPlainTextEdit()
        self.preview_box.setReadOnly(True)
        self.preview_box.setPlaceholderText("Select a row to see IR code preview...")
        self.preview_box.setStyleSheet("background-color: #121212; color: #e88004; font-family: monospace;")
        splitter.addWidget(self.preview_box)
        
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        preview_layout.addWidget(splitter)
        main_layout.addWidget(preview_group, stretch=2)

        # --- Bottom Area ---
        bottom_layout = QHBoxLayout()
        
        # Logs
        log_group = QGroupBox("Process Log")
        log_vbox = QVBoxLayout(log_group)
        self.log_window = QPlainTextEdit()
        self.log_window.setReadOnly(True)
        log_vbox.addWidget(self.log_window)
        bottom_layout.addWidget(log_group, stretch=1)
        
        # Controls
        ctrl_layout = QVBoxLayout()
        self.status_label = QLabel("Ready.")
        self.progress_bar = QProgressBar()
        self.start_btn = QPushButton("START CONVERSION")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.setStyleSheet("background-color: #e88004; color: black; font-weight: bold; padding: 10px;")
        self.start_btn.clicked.connect(self.run_conversion)
        
        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(self.status_label)
        ctrl_layout.addWidget(self.progress_bar)
        ctrl_layout.addWidget(self.start_btn)
        ctrl_layout.addWidget(self.cancel_btn)
        bottom_layout.addLayout(ctrl_layout)
        
        main_layout.addLayout(bottom_layout, stretch=1)

    def scan_for_csvs(self):
        path = self.input_entry.text()
        self.file_combo.clear()
        if os.path.isdir(path):
            files = glob.glob(os.path.join(path, "*.csv"))
            for f in files:
                self.file_combo.addItem(os.path.basename(f), f)

    def load_selected_csv(self):
        file_path = self.file_combo.currentData()
        if not file_path or not os.path.exists(file_path):
            self.table.setRowCount(0)
            return
        
        try:
            self.current_csv_df = pd.read_csv(file_path)
            self.table.setRowCount(len(self.current_csv_df))
            for i, row in self.current_csv_df.iterrows():
                self.table.setItem(i, 0, QTableWidgetItem(str(row.get('functionname', ''))))
                self.table.setItem(i, 1, QTableWidgetItem(str(row.get('protocol', ''))))
                self.table.setItem(i, 2, QTableWidgetItem(str(row.get('device', ''))))
                self.table.setItem(i, 3, QTableWidgetItem(str(row.get('subdevice', ''))))
                self.table.setItem(i, 4, QTableWidgetItem(str(row.get('function', ''))))
        except Exception as e:
            self.log(f"Error loading preview: {e}")

    def update_ir_preview(self):
        selected = self.table.currentRow()
        if selected < 0 or self.current_csv_df is None:
            return
        
        row = self.current_csv_df.iloc[selected]
        func_name = str(row.get('functionname', 'Unknown'))
        protocol = str(row.get('protocol', 'UNKNOWN'))
        addr, cmd = IRProtocolConverter.convert(protocol, row.get('device', 0), row.get('subdevice', 0), row.get('function', 0))
        
        preview = (
            "Filetype: IR signals file\n"
            "Version: 1\n"
            f"name: {func_name}\n"
            "type: parsed\n"
            f"protocol: {protocol}\n"
            f"address: {addr}\n"
            f"command: {cmd}\n"
        )
        self.preview_box.setPlainText(preview)

    def load_settings(self):
        self.input_entry.setText(self.settings.value("input_dir", ""))
        self.output_entry.setText(self.settings.value("output_dir", ""))
        self.group_checkbox.setChecked(self.settings.value("group_by_csv", "false") == "true")
        self.scan_for_csvs()

    def save_settings(self):
        self.settings.setValue("input_dir", self.input_entry.text())
        self.settings.setValue("output_dir", self.output_entry.text())
        self.settings.setValue("group_by_csv", "true" if self.group_checkbox.isChecked() else "false")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            path = files[0]
            if os.path.isdir(path): self.input_entry.setText(path)
            elif path.lower().endswith(".csv"): self.input_entry.setText(os.path.dirname(path))

    def log(self, message):
        self.log_window.appendPlainText(message)
        self.log_window.verticalScrollBar().setValue(self.log_window.verticalScrollBar().maximum())

    def browse_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder: self.input_entry.setText(folder)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder: self.output_entry.setText(folder)

    def run_conversion(self):
        input_dir = self.input_entry.text()
        output_dir = self.output_entry.text()
        if not input_dir or not output_dir:
            QMessageBox.critical(self, "Error", "Select input and output folders.")
            return
        
        self.save_settings()
        self.start_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.log_window.clear()
        
        self.thread = QThread()
        self.worker = IRConverterWorker(input_dir, output_dir, self.group_checkbox.isChecked())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.on_process_finished)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log)
        self.thread.start()

    def cancel_conversion(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.cancel_btn.setText("CANCELLING...")

    def on_process_finished(self):
        self.start_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setText("CANCEL")
        self.status_label.setText("Done.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IRConverterApp()
    window.show()
    sys.exit(app.exec())
