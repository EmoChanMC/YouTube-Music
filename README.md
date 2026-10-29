# YouTube Music Desktop

An unofficial YouTube Music desktop app for Windows, built with Python and [pywebview](https://pywebview.flowrl.com/).

> **Disclaimer:** This project is not affiliated with, endorsed by, or sponsored by Google or YouTube. YouTube Music is a trademark of Google LLC.

## Features

- Runs YouTube Music in its own window
- Remembers your login between sessions
- Minimizes to the system tray when closed (music keeps playing)
- Tray menu: show, play/pause, next, previous, always on top, quit
- Global media key support (play/pause, next, previous)
- Window title and tray tooltip show the current track
- Remembers window size, position, and "always on top" setting
- Single instance: launching it again brings the existing window to the front
- Dark scrollbar styling

## Requirements

- Windows 10 / 11 (with WebView2 runtime, usually preinstalled)
- Python 3.9+

## Download

The easiest way to get started is to download the ready-to-use executable from the [Releases page](https://github.com/EmoChanMC/YouTube-Music/releases/tag/youtube-music). No Python installation required.

1. Go to the [latest release](https://github.com/EmoChanMC/YouTube-Music/releases/tag/youtube-music)
2. Download the `.exe` file under **Assets**
3. Run it

> Windows SmartScreen may show a warning for unsigned apps. Click **More info** → **Run anyway** if you trust the source.

## Installation (from source)

```bash
git clone https://github.com/EmoChanMC/YouTube-Music.git
cd YouTube-Music
pip install pywebview pynput pystray pillow
python ytmusic_app.py
```

Project structure:

```
ytmusic_app.py
icons/
    app.ico
    app.png
```

## Build an executable

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name "YouTube Music" --icon "icons/app.ico" --add-data "icons;icons" --hidden-import pystray._win32 --hidden-import pynput.keyboard._win32 ytmusic_app.py
```

The executable will be created in the `dist` folder.

Tip: use `--onedir` instead of `--onefile` for faster startup.

## Known issues

- Google may occasionally block sign-in from embedded browsers. If that happens, try again later or sign in once through a regular browser first.
- Media key actions click buttons in the YouTube Music UI. If YouTube changes its page layout, the selectors at the top of `ytmusic_app.py` (`JS_PLAY_PAUSE`, `JS_NEXT`, `JS_PREV`) may need updating.

## Settings location

Settings and login data are stored in `%APPDATA%\ytmusic_app`.

## License

MIT
