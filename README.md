# The Grievance Log

A lightweight Python desktop app to log grievances to a Google Sheet (via a REST endpoint like Sheet.best) and view the full submission history with a Status column.

## Features

- Submit new entries with timestamp
- History view with Grievance and Status columns
- Reflects manual Status updates done directly in the Google Sheet (e.g., "Seen ✅")
- Refresh history on demand
- Clean, light UI in a non-resizable 500x550 window
 - Modern visual touches: primary button styling, zebra-striped history rows, and seen-status highlighting
 - Handy shortcuts: Ctrl+Enter to submit, F5 to refresh

## Prerequisites

- Python 3.8+ installed
- An API endpoint URL that exposes your Google Sheet, such as Sheet.best

Google Sheet columns (in order):
1. Timestamp
2. Grievance
3. Status

## Setup

1. Install dependencies

```powershell
python -m pip install --upgrade pip ; pip install -r requirements.txt
```

2. Configure the API URL

Pick one of the following:

- Environment variable (recommended)

```powershell
$env:SHEET_API_URL = "https://sheet.best/api/sheets/your-sheet-id-here"
```

- Config file (create `config.json` next to `app.py`)

```json
{
	"SHEET_API_URL": "https://sheet.best/api/sheets/your-sheet-id-here"
}
```

You can copy `config.example.json` to `config.json` and edit the value.

## Run the app

```powershell
python app.py
```

When the app starts, it will fetch and display all existing rows. Submitting a new entry will POST to the API and automatically refresh the history.

### Run the Streamlit web app

```powershell
# Ensure deps are installed
pip install -r requirements.txt

# Launch Streamlit UI
streamlit run app_streamlit.py
```

The web UI provides a form for submission and shows each entry in an expandable panel with timestamp and status.

### Customize color scheme and images (Streamlit)

The Streamlit app ships with a light pink background and pink primary buttons. You can tweak this by editing the small CSS block in `app_streamlit.py` (search for `st.markdown(<style>...)`).

You can also add images (optional):

- `HEADER_IMAGE`: Shown under the title (full width)
- `SIDEBAR_IMAGE`: Shown in the sidebar (full width)
- `FOOTER_IMAGE`: Shown at the bottom (full width)

Provide paths or URLs via environment variables or `config.json`:

```powershell
$env:HEADER_IMAGE = "C:\\path\\to\\header.png"
$env:SIDEBAR_IMAGE = "https://example.com/sidebar.jpg"
$env:FOOTER_IMAGE = "C:\\path\\to\\footer.png"
```

Or add them to `config.json` next to the `SHEET_API_URL`.

#### Recommended images folder and names

You can place images in an `images/` folder at the project root. The app will auto-detect these filenames if env/config values are not set:

- `images/header.(png|jpg|jpeg|webp)` → Header image
- `images/sidebar.(png|jpg|jpeg|webp)` → Sidebar image
- `images/footer.(png|jpg|jpeg|webp)` → Footer image

Priority order for each image slot:
1. Environment variable (e.g., `HEADER_IMAGE`)
2. `config.json` value
3. Auto-detected file in `images/`

## Building a Windows EXE with PyInstaller

1. Install PyInstaller

```powershell
pip install pyinstaller
```

2. Build

```powershell
pyinstaller --noconfirm --clean --onefile --windowed --name "TheGrievanceLog" app.py
```

This creates `dist/TheGrievanceLog.exe`.

3. Distribute config (optional)

If you prefer using a config file instead of an environment variable, place `config.json` in the same folder as the EXE. The app will detect it at runtime.

## API contract

The app expects GET to return a JSON array of objects with keys:

```json
[
	{
		"Timestamp": "2025-09-22T12:34:56",
		"Grievance": "Example text",
		"Status": "Seen ✅"
	}
]
```

POST payload sent by the app:

```json
{
	"Timestamp": "<ISO8601 seconds>",
	"Grievance": "<user text>",
	"Status": ""
}
```

## Notes

- Network errors are shown as popups; use the Refresh button to retry.
- If both an environment variable and a config file are present, the environment variable wins.
- The app uses threading for non-blocking network calls and will remain responsive.
