"""Responsive read-only junk scan page."""
from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
from app.core.junk_scanner import scan_temp, user_temp_directory


def human_size(size):
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if size < 1024 or unit == 'TB':
            return f'{size:.1f} {unit}'
        size /= 1024


class ScanWorker(QObject):
    progress = Signal(int, int)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self):
        super().__init__()
        self._cancel = False

    def cancel(self):
        self._cancel = True

    @Slot()
    def run(self):
        try:
            result = scan_temp(progress=lambda n, b: self.progress.emit(n, b),
                               cancelled=lambda: self._cancel)
            self.finished.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class CleanerPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        title = QLabel('Junk Scanner')
        title.setObjectName('title')
        layout.addWidget(title)
        note = QLabel('Read-only scan of your Windows user temp folder. No files will be deleted.')
        note.setWordWrap(True)
        note.setObjectName('muted')
        layout.addWidget(note)
        folder = QLabel(f'Scan target: {user_temp_directory()}')
        folder.setWordWrap(True)
        folder.setObjectName('muted')
        layout.addWidget(folder)
        actions = QHBoxLayout()
        self.scan_button = QPushButton('Start Scan')
        self.scan_button.setObjectName('active')
        self.scan_button.clicked.connect(self.start_scan)
        actions.addWidget(self.scan_button)
        self.cancel_button = QPushButton('Cancel')
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_scan)
        actions.addWidget(self.cancel_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.status = QLabel('Ready to scan')
        self.status.setObjectName('muted')
        layout.addWidget(self.status)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['File path (sample: up to 1,000)', 'Size'])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        self._thread = None
        self._worker = None

    def start_scan(self):
        if self._thread is not None:
            return
        self.table.setRowCount(0)
        self.status.setText('Scanning...')
        self.scan_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self._thread = QThread(self)
        self._worker = ScanWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_progress)
        self._worker.finished.connect(self.on_result)
        self._worker.failed.connect(self.on_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self.on_thread_finished)
        self._thread.start()

    def cancel_scan(self):
        if self._worker:
            self._worker.cancel()
            self.status.setText('Stopping scan...')
            self.cancel_button.setEnabled(False)

    def on_progress(self, count, size):
        self.status.setText(f'Scanning... {count:,} files · {human_size(size)}')

    def on_result(self, result):
        for path, size in result['samples']:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(path))
            self.table.setItem(row, 1, QTableWidgetItem(human_size(size)))
        qualifier = ' (partial scan)' if result['partial'] else ''
        self.status.setText(f"Found {result['files']:,} files · {human_size(result['bytes'])} · "
                            f"{result['errors']} inaccessible entries{qualifier}. "
                            'These are temp files, not necessarily safe to delete.')

    def on_error(self, message):
        self.status.setText(f'Scan failed: {message}')

    def on_thread_finished(self):
        self._thread = None
        self._worker = None
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def closeEvent(self, event):
        if self._thread is not None:
            self.cancel_scan()
            event.ignore()
            self.status.setText('Wait for the scan to stop before closing.')
            return
        super().closeEvent(event)
