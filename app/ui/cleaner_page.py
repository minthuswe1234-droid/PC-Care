"""Temp scan and explicitly selected recycle-bin cleanup."""
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QTableWidget,
                              QTableWidgetItem, QVBoxLayout, QWidget, QMessageBox,
                              QAbstractItemView)
from app.core.junk_scanner import scan_temp, user_temp_directory
from app.core.safe_cleanup import recycle_selected


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
            self.finished.emit(scan_temp(progress=lambda n, b: self.progress.emit(n, b),
                                         cancelled=lambda: self._cancel))
        except Exception as exc:
            self.failed.emit(str(exc))


class CleanupWorker(QObject):
    finished = Signal(dict)
    def __init__(self, items):
        super().__init__()
        self.items = items

    @Slot()
    def run(self):
        self.finished.emit(recycle_selected(self.items))


class CleanerPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        title = QLabel('Safe Junk Cleaner')
        title.setObjectName('title')
        layout.addWidget(title)
        note = QLabel('Scans user temp only. Select files manually. Selected files go to Recycle Bin, never permanent delete. Files in use may fail.')
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
        self.cancel_button = QPushButton('Cancel Scan')
        self.cancel_button.clicked.connect(self.cancel_scan)
        self.cancel_button.setEnabled(False)
        actions.addWidget(self.cancel_button)
        self.clean_button = QPushButton('Recycle Selected')
        self.clean_button.clicked.connect(self.clean_selected)
        self.clean_button.setEnabled(False)
        actions.addWidget(self.clean_button)
        actions.addStretch()
        layout.addLayout(actions)
        self.status = QLabel('Ready to scan')
        self.status.setObjectName('muted')
        layout.addWidget(self.status)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(['File path (up to 1,000)', 'Size'])
        self.table.horizontalHeader().setSectionResizeMode(0, self.table.horizontalHeader().ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        self._samples = []
        self._thread = None
        self._worker = None
        self._busy = None

    def _start_worker(self, worker, kind):
        self._busy = kind
        self._thread = QThread(self)
        self._worker = worker
        worker.moveToThread(self._thread)
        self._thread.started.connect(worker.run)
        worker.finished.connect(self.on_result if kind == 'scan' else self.on_cleaned)
        worker.finished.connect(self._thread.quit)
        if kind == 'scan':
            worker.progress.connect(self.on_progress)
            worker.failed.connect(self.on_error)
            worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self.on_thread_finished)
        self._thread.start()

    def start_scan(self):
        if self._thread is not None:
            return
        self.table.setRowCount(0)
        self._samples = []
        self.status.setText('Scanning...')
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self._start_worker(ScanWorker(), 'scan')

    def cancel_scan(self):
        if self._busy == 'scan' and self._worker:
            self._worker.cancel()
            self.cancel_button.setEnabled(False)
            self.status.setText('Stopping scan...')

    def on_progress(self, count, size):
        self.status.setText(f'Scanning... {count:,} files · {human_size(size)}')

    def on_result(self, result):
        self._samples = result['samples']
        for path, size, mtime in self._samples:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(path))
            self.table.setItem(row, 1, QTableWidgetItem(human_size(size)))
        qualifier = ' (partial)' if result['partial'] else ''
        self.status.setText(f"Found {result['files']:,} files · {human_size(result['bytes'])} · {result['errors']} errors{qualifier}. Select rows to recycle; temp files are not necessarily safe to remove.")
        self.clean_button.setEnabled(bool(self._samples))

    def clean_selected(self):
        if self._thread is not None:
            return
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, 'Select files', 'Select one or more rows first.')
            return
        items = [self._samples[i] for i in rows]
        size = sum(item[1] for item in items)
        answer = QMessageBox.question(self, 'Confirm Recycle',
            f'Send {len(items)} selected temp files ({human_size(size)}) to Recycle Bin?\n\nFiles in use may fail. This cannot guarantee recovery.')
        if answer != QMessageBox.StandardButton.Yes:
            return
        self.scan_button.setEnabled(False)
        self.clean_button.setEnabled(False)
        self.status.setText('Recycling selected files...')
        self._start_worker(CleanupWorker(items), 'clean')

    def on_cleaned(self, result):
        recycled = result['recycled']
        locked = result.get('skipped_locked', 0)
        gone = result.get('already_gone', 0)
        changed = result.get('changed', 0)
        failed = result['failed']
        self.status.setText(
            f"Recycled {recycled} ({human_size(result['bytes'])}) · "
            f"Locked/skipped {locked} · Already gone {gone} · "
            f"Changed {changed} · Other failures {len(failed)}. Scan again to refresh."
        )
        self._samples = []
        self.table.setRowCount(0)
        self.clean_button.setEnabled(False)
        if failed:
            QMessageBox.warning(self, 'Some files could not be recycled',
                '\n'.join(f'{path}: {error}' for path, error in failed[:5]))

    def on_error(self, message):
        self.status.setText(f'Scan failed: {message}')

    def on_thread_finished(self):
        self._thread = None
        self._worker = None
        self._busy = None
        self.scan_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

    def closeEvent(self, event):
        if self._thread is not None:
            self.cancel_scan()
            event.ignore()
            self.status.setText('Wait for the current operation to finish before closing.')
            return
        super().closeEvent(event)
