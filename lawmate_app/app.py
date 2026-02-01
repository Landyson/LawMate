from __future__ import annotations

from pathlib import Path
from PySide6.QtWidgets import QApplication

from lawmate_app.config import AppConfig
from lawmate_app.db import Database
from lawmate_app.ui.main_window import MainWindow

def run_app() -> None:
    cfg = AppConfig.load()

    app = QApplication([])
    app.setApplicationName("Lawmate")

    data_dir = Path.home() / ".lawmate"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / "lawmate.sqlite3"
    db = Database(db_path)

    win = MainWindow(cfg=cfg, db=db)
    win.resize(1100, 720)
    win.show()

    app.exec()
