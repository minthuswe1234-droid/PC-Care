"""Read-only disk analysis with background scanning and local history."""
import threading
from pathlib import Path
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QFileDialog, QTableWidget, QTableWidgetItem, QMessageBox)
from app.core.disk_analyzer import analyze_folder
from app.core.scan_history import save_scan, recent_scans
from app.ui.cleaner_page import human_size


class DiskWorker(QObject):
    progress = Signal(int, int)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, folder, cancel_event):
        super().__init__()
        self.folder = folder
        self.cancel_event = cancel_event

    @Slot()
    def run(self):
        try:
            result = analyze_folder(self.folder, cancelled=self.cancel_event.is_set,
                                    progress=lambda n, b: self.progress.emit(n, b))
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class DiskPage(QWidget):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.cancel_event = threading.Event()
        layout = QVBoxLayout(self)
        heading = QLabel('Disk Analyzer — Read Only')
        heading.setObjectName('title')
        layout.addWidget(heading)
        controls = QHBoxLayout()
        self.folder_label = QLabel('Choose a folder to analyze')
        controls.addWidget(self.folder_label, 1)
        self.choose = QPushButton('Choose Folder')
        self.choose.clicked.connect(self.choose_folder)
        controls.addWidget(self.choose)
        self.stop = QPushButton('Cancel')
        self.stop.setEnabled(False)
        self.stop.clicked.connect(self.cancel_event.set)
        controls.addWidget(self.stop)
        layout.addLayout(controls)
        self.status = QLabel('Ready')
        layout.addWidget(self.status)
        layout.addWidget(QLabel('Largest direct subfolders (includes nested contents)'))
        self.folders = self.make_table(['Folder', 'Size'])
        layout.addWidget(self.folders, 1)
        layout.addWidget(QLabel('Largest files'))
        self.files = self.make_table(['File', 'Size'])
        layout.addWidget(self.files, 1)
        layout.addWidget(QLabel('Recent scans (stored locally)'))
        self.history = self.make_table(['Date (UTC)', 'Folder', 'Files', 'Size'])
        layout.addWidget(self.history, 1)
        self.refresh_history()

    @staticmethod
    def make_table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    @staticmethod
    def populate(table, rows):
        table.setRowCount(0)
        for values in rows:
            index = table.rowCount()
            table.insertRow(index)
            for col, value in enumerate(values):
                table.setItem(index, col, QTableWidgetItem(str(value)))

    def choose_folder(self):
        if self.thread is not None:
            return
        folder = QFileDialog.getExistingDirectory(self, 'Choose folder to analyze', str(Path.home()))
        if not folder:
            return
        self.folder_label.setText(folder)
        self.cancel_event.clear()
        self.choose.setEnabled(False)
        self.stop.setEnabled(True)
        self.status.setText('Scanning...')
        self.thread = QThread(self)
        self.worker = DiskWorker(folder, self.cancel_event)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_result)
        self.worker.failed.connect(self.on_error)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.on_done)
        self.thread.start()

    def on_progress(self, files, size):
        self.status.setText(f'Scanning {files:,} files · {human_size(size)}')

    def on_result(self, result):
        self.populate(self.folders, [(name, human_size(size)) for name, size in result['folders']])
        self.populate(self.files, [(name, human_size(size)) for size, name in result['largest']])
        self.status.setText(f"Scanned {result['files']:,} files · {human_size(result['bytes'])} · {result['errors']} inaccessible · {'Partial' if result['partial'] else 'Complete'}")
        try:
            save_scan(result)
            self.refresh_history()
        except OSError as exc:
            QMessageBox.warning(self, 'History not saved', str(exc))

    def on_error(self, message):
        self.status.setText('Scan failed: ' + message)

    def on_done(self):
        self.thread = None
        self.worker = None
        self.choose.setEnabled(True)
        self.stop.setEnabled(False)

    def refresh_history(self):
        try:
            self.populate(self.history, [(date, root, files, human_size(size))
                                         for date, root, files, size, errors, partial in recent_scans()])
        except OSError:
            self.populate(self.history, [])

    def closeEvent(self, event):
        if self.thread is not None:
            self.cancel_event.set()
            event.ignore()
            self.status.setText('Wait for scan to stop before closing')
        else:
            super().closeEvent(event)
