import sys
import os
import glob
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QPlainTextEdit,
    QFileDialog, QMessageBox, QGroupBox, QCheckBox
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
    margin-top: 24px;
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
QLineEdit {
    background-color: #3b3b3b;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 6px;
    color: #eee;
    selection-background-color: #e88004;
}
QLineEdit:focus {
    border: 1px solid #e88004;
}
QPushButton {
    background-color: #444;
    border: 1px solid #555;
    border-radius: 4px;
    padding: 6px 12px;
    color: #fff;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #555;
    border-color: #666;
}
QPushButton:pressed {
    background-color: #e88004;
    border-color: #e88004;
    color: #000;
}
QPushButton#PrimaryButton {
    background-color: #e88004;
    border: 1px solid #e88004;
    color: #000;
    font-size: 15px;
    padding: 8px 20px;
}
QPushButton#PrimaryButton:hover {
    background-color: #ff9d2e;
    border-color: #ff9d2e;
}
QPushButton#PrimaryButton:pressed {
    background-color: #c76e03;
    border-color: #c76e03;
}
QPushButton#CancelButton {
    background-color: #cc0000;
    border: 1px solid #cc0000;
    color: #fff;
}
QPushButton#CancelButton:hover {
    background-color: #ff0000;
}
QPushButton:disabled {
    background-color: #333;
    border-color: #444;
    color: #777;
}
QProgressBar {
    border: 1px solid #555;
    border-radius: 4px;
    text-align: center;
    background-color: #3b3b3b;
    color: white;
}
QProgressBar::chunk {
    background-color: #e88004;
    width: 1px;
}
QPlainTextEdit {
    background-color: #1e1e1e;
    border: 1px solid #444;
    border-radius: 4px;
    color: #00ff00;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    padding: 8px;
}
QLabel#HeaderLabel {
    font-size: 24px;
    font-weight: bold;
    color: #e88004;
    margin-bottom: 10px;
}
QLabel#SubHeaderLabel {
    color: #aaa;
    margin-bottom: 20px;
}
QCheckBox {
    spacing: 10px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
}
"""

class IRProtocolConverter:
    """Handles logic for various IR protocols."""
    
    @staticmethod
    def convert(protocol, device, subdevice, function):
        try:
            p = protocol.upper()
            d = int(device)
            s = int(subdevice)
            f = int(function)

            if p == "NEC":
                # NEC: address is dev(8bit) + sub(8bit), command is func(8bit) + ~func(8bit)
                addr_hex = f"{d:02X} {s:02X} 00 00"
                cmd_hex = f"{f:02X} {(~f & 0xFF):02X} 00 00"
                return addr_hex, cmd_hex
            
            elif p == "SAMSUNG":
                # Samsung: 32-bit protocol, address often dev + sub
                addr_hex = f"{d:02X} {s:02X} 00 00"
                cmd_hex = f"{f:02X} 00 00 00"
                return addr_hex, cmd_hex
            
            elif p == "SONY":
                # Sony: 12, 15, or 20 bits. Usually address is device.
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
                    # Single remote file mode
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
                    # Individual files mode
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
        self.resize(800, 700)
        self.setAcceptDrops(True)
        
        self.settings = QSettings("Exzploit", "FlipperIRConverter")
        
        # Apply Dark Theme
        self.setStyleSheet(FLIPPER_THEME)
        
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        # --- Header ---
        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        
        title = QLabel("FLIPPER IR CONVERTER")
        title.setObjectName("HeaderLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("Batch convert CSV remotes to .ir format")
        subtitle.setObjectName("SubHeaderLabel")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addLayout(header_layout)

        # --- Configuration Group ---
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(15)
        config_layout.setContentsMargins(20, 25, 20, 20)

        # Input Row
        input_layout = QHBoxLayout()
        self.input_entry = QLineEdit()
        self.input_entry.setPlaceholderText("Select Input Folder (or drag & drop here)...")
        browse_input_btn = QPushButton("Browse...")
        browse_input_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_input_btn.clicked.connect(self.browse_input)
        
        input_layout.addWidget(QLabel("Input:"))
        input_layout.addWidget(self.input_entry)
        input_layout.addWidget(browse_input_btn)
        config_layout.addLayout(input_layout)

        # Output Row
        output_layout = QHBoxLayout()
        self.output_entry = QLineEdit()
        self.output_entry.setPlaceholderText("Select Output Folder (for .ir files)...")
        browse_output_btn = QPushButton("Browse...")
        browse_output_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_output_btn.clicked.connect(self.browse_output)
        
        output_layout.addWidget(QLabel("Output:"))
        output_layout.addWidget(self.output_entry)
        output_layout.addWidget(browse_output_btn)
        config_layout.addLayout(output_layout)

        # Options Row
        self.group_checkbox = QCheckBox("Group signals from each CSV into a single .ir remote file")
        config_layout.addWidget(self.group_checkbox)

        main_layout.addWidget(config_group)

        # --- Progress Area ---
        progress_layout = QVBoxLayout()
        self.status_label = QLabel("Ready to start...")
        self.status_label.setStyleSheet("color: #888; font-style: italic;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        main_layout.addLayout(progress_layout)

        # --- Log Window ---
        log_group = QGroupBox("Process Log")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(10, 20, 10, 10)
        
        self.log_window = QPlainTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setPlaceholderText("Waiting for process to start...")
        log_layout.addWidget(self.log_window)
        
        main_layout.addWidget(log_group, stretch=1)

        # --- Footer / Action ---
        footer_layout = QHBoxLayout()
        footer_layout.addStretch()
        
        self.start_btn = QPushButton("START CONVERSION")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.run_conversion)
        
        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.setObjectName("CancelButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        self.cancel_btn.setVisible(False)
        
        footer_layout.addWidget(self.start_btn)
        footer_layout.addWidget(self.cancel_btn)
        footer_layout.addStretch()
        
        main_layout.addLayout(footer_layout)

    def load_settings(self):
        self.input_entry.setText(self.settings.value("input_dir", ""))
        self.output_entry.setText(self.settings.value("output_dir", ""))
        self.group_checkbox.setChecked(self.settings.value("group_by_csv", "false") == "true")

    def save_settings(self):
        self.settings.setValue("input_dir", self.input_entry.text())
        self.settings.setValue("output_dir", self.output_entry.text())
        self.settings.setValue("group_by_csv", "true" if self.group_checkbox.isChecked() else "false")

    # Drag & Drop Support
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            path = files[0]
            if os.path.isdir(path):
                self.input_entry.setText(path)
            elif os.path.isfile(path) and path.lower().endswith(".csv"):
                self.input_entry.setText(os.path.dirname(path))

    def log(self, message):
        self.log_window.appendPlainText(message)
        scrollbar = self.log_window.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def browse_input(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.input_entry.setText(folder)

    def browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_entry.setText(folder)

    def run_conversion(self):
        input_dir = self.input_entry.text()
        output_dir = self.output_entry.text()

        if not input_dir or not output_dir:
            QMessageBox.critical(self, "Error", "Please select both input and output folders.")
            return

        csv_files = glob.glob(os.path.join(input_dir, "*.csv"))
        if not csv_files:
            QMessageBox.warning(self, "No Files", "No CSV files found in the input folder.")
            return

        self.save_settings()

        # Reset UI state
        self.start_btn.setEnabled(False)
        self.start_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        
        self.log_window.clear()
        self.log("--- Initialization ---")
        self.log(f"Input: {input_dir}")
        self.log(f"Output: {output_dir}")
        self.log(f"Mode: {'Single Remote File' if self.group_checkbox.isChecked() else 'Individual Files'}")
        self.log(f"Found {len(csv_files)} files.")
        self.log("----------------------")
        
        self.status_label.setText("Processing files...")
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(csv_files))

        # Threading
        self.thread = QThread()
        self.worker = IRConverterWorker(input_dir, output_dir, self.group_checkbox.isChecked())
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_process_finished)

        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log)
        self.worker.error.connect(lambda msg: QMessageBox.critical(self, "Error", msg))

        self.thread.start()

    def cancel_conversion(self):
        if hasattr(self, 'worker'):
            self.worker.stop()
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText("CANCELLING...")

    def on_process_finished(self):
        self.start_btn.setEnabled(True)
        self.start_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)
        self.cancel_btn.setText("CANCEL")
        
        if hasattr(self, 'worker') and self.worker.is_cancelled:
            self.status_label.setText("Process cancelled.")
        else:
            self.status_label.setText("Batch processing complete.")
            self.log("----------------------")
            self.log("✓ All tasks completed successfully.")
            QMessageBox.information(self, "Success", "Conversion process completed!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = IRConverterApp()
    window.show()
    sys.exit(app.exec())
