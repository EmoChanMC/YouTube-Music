"""
YouTube Music Masaüstü Uygulaması

Kurulum:
    pip install pywebview pynput pystray pillow

Çalıştırma:
    python ytmusic_app.py

Klasör yapısı:
    ytmusic_app.py
    icons/
        app.ico
        app.png

Özellikler:
  - YouTube Music kendi penceresinde açılır, oturum hatırlanır
  - Pencereyi kapatınca uygulama sistem tepsisine küçülür (müzik çalmaya devam eder)
  - Tepsi menüsü: göster/gizle, oynat/duraklat, sonraki, önceki, her zaman üstte, çıkış
  - Medya tuşları global olarak çalışır
  - Pencere başlığı ve tepsi ipucu çalan şarkıyı gösterir
  - Pencere boyutu, konumu ve "her zaman üstte" ayarı hatırlanır
  - Uygulama tek örnek çalışır (ikinci kez açılırsa mevcut pencere öne gelir)
  - Koyu temalı kaydırma çubuğu
"""

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

import webview

# ----------------------------------------------------------------------------
# Sabitler ve yollar
# ----------------------------------------------------------------------------
APP_NAME = "YouTube Music"
URL = "https://music.youtube.com"
SINGLE_INSTANCE_PORT = 48653


def resource_path(relative: str) -> Path:
    """PyInstaller ile paketlenmiş ya da normal çalışmada dosya yolunu bulur."""
    base = getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    return Path(base) / relative


APP_DIR = Path(os.getenv("APPDATA") or Path.home() / ".config") / "ytmusic_app"
STORAGE_DIR = APP_DIR / "webview_data"
SETTINGS_FILE = APP_DIR / "settings.json"
ICON_PNG = resource_path("icons/app.png")
ICON_ICO = resource_path("icons/app.ico")

APP_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# YouTube Music arayüzündeki düğmeler
JS_PLAY_PAUSE = "document.querySelector('ytmusic-player-bar #play-pause-button')?.click();"
JS_NEXT = "document.querySelector('ytmusic-player-bar .next-button')?.click();"
JS_PREV = "document.querySelector('ytmusic-player-bar .previous-button')?.click();"

# Koyu kaydırma çubuğu
JS_INJECT_CSS = """
(function () {
  if (document.getElementById('ytm-desktop-style')) return;
  const s = document.createElement('style');
  s.id = 'ytm-desktop-style';
  s.textContent = `
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #3a3a3a; border-radius: 6px; }
    ::-webkit-scrollbar-thumb:hover { background: #5a5a5a; }
  `;
  document.head.appendChild(s);
})();
"""

# ----------------------------------------------------------------------------
# Durum
# ----------------------------------------------------------------------------
state = {
    "quitting": False,
    "on_top": False,
    "tray": None,
    "window": None,
    "loaded_once": False,
}


# ----------------------------------------------------------------------------
# Ayarlar
# ----------------------------------------------------------------------------
def load_settings() -> dict:
    default = {"width": 1100, "height": 750, "x": None, "y": None, "on_top": False}
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        default.update(data)
    except Exception:
        pass
    return default


def save_settings(window) -> None:
    try:
        data = {
            "width": window.width,
            "height": window.height,
            "x": window.x,
            "y": window.y,
            "on_top": state["on_top"],
        }
        SETTINGS_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception as e:
        print("Ayarlar kaydedilemedi:", e)


# ----------------------------------------------------------------------------
# Tek örnek kontrolü
# ----------------------------------------------------------------------------
def ensure_single_instance():
    """Port zaten doluysa mevcut örneğe 'göster' sinyali gönderip çıkar."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        sock.listen(1)
        return sock
    except OSError:
        try:
            with socket.create_connection(("127.0.0.1", SINGLE_INSTANCE_PORT), timeout=1) as c:
                c.sendall(b"show")
        except OSError:
            pass
        sys.exit(0)


def listen_for_show(sock) -> None:
    while True:
        try:
            conn, _ = sock.accept()
            with conn:
                if conn.recv(16) == b"show":
                    show_window()
        except OSError:
            break


# ----------------------------------------------------------------------------
# Pencere işlemleri
# ----------------------------------------------------------------------------
def js(code: str) -> None:
    try:
        state["window"].evaluate_js(code)
    except Exception:
        pass


def play_pause(*_):
    js(JS_PLAY_PAUSE)


def next_track(*_):
    js(JS_NEXT)


def prev_track(*_):
    js(JS_PREV)


def show_window(*_):
    w = state["window"]
    if w:
        try:
            w.show()
            w.restore()
        except Exception:
            pass


def hide_window(*_):
    w = state["window"]
    if w:
        try:
            w.hide()
        except Exception:
            pass


def toggle_window(*_):
    """Tepsi simgesine tıklayınca göster/gizle."""
    show_window()


def toggle_on_top(*_):
    state["on_top"] = not state["on_top"]
    try:
        state["window"].on_top = state["on_top"]
    except Exception:
        pass


def quit_app(*_):
    state["quitting"] = True
    tray = state["tray"]
    if tray:
        try:
            tray.stop()
        except Exception:
            pass
    w = state["window"]
    if w:
        save_settings(w)
        try:
            w.destroy()
        except Exception:
            pass


# ----------------------------------------------------------------------------
# Sistem tepsisi
# ----------------------------------------------------------------------------
def start_tray() -> None:
    try:
        import pystray
        from PIL import Image
    except ImportError:
        print("pystray/pillow yüklü değil, sistem tepsisi devre dışı.")
        return

    try:
        image = Image.open(ICON_PNG)
    except Exception:
        image = Image.new("RGB", (64, 64), "#ff0033")

    menu = pystray.Menu(
        pystray.MenuItem("Göster", toggle_window, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Oynat / Duraklat", play_pause),
        pystray.MenuItem("Sonraki", next_track),
        pystray.MenuItem("Önceki", prev_track),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            "Her zaman üstte",
            toggle_on_top,
            checked=lambda item: state["on_top"],
        ),
        pystray.MenuItem("Çıkış", quit_app),
    )

    tray = pystray.Icon("ytmusic_app", image, APP_NAME, menu)
    state["tray"] = tray
    tray.run_detached()


# ----------------------------------------------------------------------------
# Medya tuşları
# ----------------------------------------------------------------------------
def start_media_keys() -> None:
    try:
        from pynput import keyboard
    except ImportError:
        print("pynput yüklü değil, medya tuşları devre dışı.")
        return

    def on_press(key):
        if key == keyboard.Key.media_play_pause:
            play_pause()
        elif key == keyboard.Key.media_next:
            next_track()
        elif key == keyboard.Key.media_previous:
            prev_track()

    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()


# ----------------------------------------------------------------------------
# Başlık takibi (çalan şarkı)
# ----------------------------------------------------------------------------
def title_watcher() -> None:
    last = ""
    while not state["quitting"]:
        time.sleep(2)
        try:
            title = state["window"].evaluate_js("document.title")
        except Exception:
            continue
        if not title or title == last:
            continue
        last = title
        try:
            state["window"].set_title(title)
        except Exception:
            pass
        tray = state["tray"]
        if tray:
            try:
                tray.title = title[:120]
            except Exception:
                pass


# ----------------------------------------------------------------------------
# Olaylar
# ----------------------------------------------------------------------------
def on_loaded() -> None:
    js(JS_INJECT_CSS)
    if not state["loaded_once"]:
        state["loaded_once"] = True
        threading.Thread(target=start_media_keys, daemon=True).start()
        threading.Thread(target=title_watcher, daemon=True).start()


def on_closing():
    """Kapat düğmesi: gerçekten çıkmıyorsak tepsiye küçült."""
    if state["quitting"] or state["tray"] is None:
        save_settings(state["window"])
        return True
    save_settings(state["window"])
    hide_window()
    return False  # kapatmayı iptal et


# ----------------------------------------------------------------------------
# Ana program
# ----------------------------------------------------------------------------
def main() -> None:
    lock = ensure_single_instance()
    threading.Thread(target=listen_for_show, args=(lock,), daemon=True).start()

    s = load_settings()
    state["on_top"] = bool(s.get("on_top"))

    window = webview.create_window(
        APP_NAME,
        URL,
        width=s["width"],
        height=s["height"],
        x=s["x"],
        y=s["y"],
        min_size=(800, 500),
        background_color="#0f0f0f",
        on_top=state["on_top"],
    )
    state["window"] = window

    window.events.loaded += on_loaded
    window.events.closing += on_closing

    start_tray()

    webview.start(
        private_mode=False,
        storage_path=str(STORAGE_DIR),
        icon=str(ICON_ICO) if (sys.platform == "win32" and ICON_ICO.exists()) else None,
    )

    # Pencere gerçekten kapandıktan sonra temizlik
    state["quitting"] = True
    if state["tray"]:
        try:
            state["tray"].stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
