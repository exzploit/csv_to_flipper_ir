# Flipper IR Converter GUI

A sleek, dark-themed desktop application to batch convert CSV-formatted remote control data into Flipper Zero `.ir` files.

![Flipper IR Converter](https://img.shields.io/badge/Flipper%20Zero-Converter-orange)
![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue)

## Features
- **Batch Processing**: Select a folder and convert all CSV files at once.
- **Dark Theme**: Custom UI inspired by the Flipper Zero aesthetic.
- **Support for NEC & Hex protocols**: Automatically handles address and command conversions.
- **Live Logging**: Real-time feedback on the conversion process.

## Installation

### For Users
Download the latest version from the [Releases](https://github.com/exzploit/csv_to_flipper_ir/releases) page.
- **macOS**: Download `csv_to_flipper_ir_mac.zip`, unzip, and run the `.app`.
- **Windows**: (Coming soon via GitHub Actions)

### For Developers
1. Clone the repository:
   ```bash
   git clone https://github.com/exzploit/csv_to_flipper_ir.git
   cd csv_to_flipper_ir
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or
   venv\Scripts\activate     # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python csv_to_flipper_ir.py
   ```

## CSV Format Requirements
The converter expects `.csv` files with the following columns:
- `functionname`: The name of the button (e.g., "Power", "Volume_Up").
- `protocol`: The IR protocol (e.g., "NEC").
- `device`: The device address (integer).
- `subdevice`: The sub-device address (integer).
- `function`: The command/function code (integer).

Example:
| functionname | protocol | device | subdevice | function |
|--------------|----------|--------|-----------|----------|
| Power        | NEC      | 128    | 0         | 1        |
| Mute         | NEC      | 128    | 0         | 2        |

## Building from Source
To create your own standalone executable:
```bash
pyinstaller --onefile --windowed csv_to_flipper_ir.py
```

## License
MIT License - feel free to use and modify!
