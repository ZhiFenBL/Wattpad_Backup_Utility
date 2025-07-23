# Wattpad Backup Utility

A python script that automatically downloads and organizes all the fics an account has added to their library.

### Usage:

Using a virtual environment is recommended **(optional)**:
```bash
mkdir venv
python -m venv venv
venv/bin/activate (or source venv/bin/activate in MacOS)
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run script:
```bash
python src/main.py
```

Optional: To create executable
```bash
pyinstaller --onefile --name WattpadBackup --paths src src/main.py
```
