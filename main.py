import sys
import os
import time
import webbrowser
import threading
import subprocess
from pathlib import Path
import uvicorn

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
FRONTEND_DIST = FRONTEND_DIR / "dist"


def build_frontend_if_needed():
    """
    Controleert of de React frontend gebouwd is in frontend/dist.
    Zo niet, bouwt deze automatisch via npm run build.
    """
    if not (FRONTEND_DIST / "index.html").exists():
        print("Frontend build ontbreekt. Automatisch bouwen via 'npm run build'...")
        try:
            subprocess.run(["npm", "run", "build"], cwd=str(FRONTEND_DIR), check=True)
            print("Frontend succesvol gebouwd!")
        except Exception as e:
            print(f"Waarschuwing: Kon frontend niet automatisch compileren: {e}")
            print("U kunt de frontend handmatig draaien via: cd frontend && npm run dev")


def open_browser(url: str, delay_seconds: float = 1.2):
    """
    Opent de webpagina automatisch in de standaard webbrowser na een korte wachttijd.
    """
    def _open():
        time.sleep(delay_seconds)
        print(f"Browser openen op: {url}")
        webbrowser.open(url)

    thread = threading.Thread(target=_open, daemon=True)
    thread.start()


def main():
    print("=" * 65)
    print("  Luidsprekerconus Optimalisatie Studio - Launcher")
    print("  Zelflerend optimalisatieprogramma voor 3D-printbare conussen")
    print("=" * 65)

    build_frontend_if_needed()

    host = "127.0.0.1"
    port = 8000
    url = f"http://{host}:{port}"

    # Open webbrowser automatisch
    open_browser(url)

    print(f"\nServer wordt gestart op {url}")
    print("Druk op Ctrl+C om het programma af te sluiten.\n")

    # Start FastAPI applicatie
    uvicorn.run("backend.cone_opt.api:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
