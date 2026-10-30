import psutil
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMainWindow, QProgressBar, QStackedWidget,
    QPushButton, QVBoxLayout, QWidget, QMessageBox
)
from app.core.system_info import system_snapshot
from app.ui.cleaner_page import CleanerPage

STYLE = '''
QWidget { background: #0d1424; color: #e8eefc; font-family: 'Segoe UI'; font-size: 14px; }
QFrame#sidebar { background: #131f33; border-radius: 16px; }
QFrame#card { background: #192840; border: 1px solid #2b3b54; border-radius: 14px; }
QLabel#title { font-size: 28px; font-weight: 700; }
QLabel#heading { font-size: 19px; font-weight: 600; }
QLabel#metric { font-size: 28px; font-weight: 700; color: #69d8d0; }
QLabel#muted { color: #a6b7d1; }
QPushButton { text-align: left; padding: 12px; background: transparent; border: none; border-radius: 9px; }
QPushButton:hover { background: #263d5c; }
QPushButton#active { background: #215c73; font-weight: 600; }
QProgressBar { background: #0f1a2c; border: none; border-radius: 6px; height: 12px; text-align: center; }
QProgressBar::chunk { background: #46c6b6; border-radius: 6px; }
'''


class MetricCard(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName('card')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        heading = QLabel(title)
        heading.setObjectName('heading')
        self.value = QLabel('—')
        self.value.setObjectName('metric')
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.detail = QLabel('Collecting data...')
        self.detail.setObjectName('muted')
        layout.addWidget(heading)
        layout.addWidget(self.value)
        layout.addWidget(self.bar)
        layout.addWidget(self.detail)

    def update_metric(self, percent, detail):
        self.value.setText(f'{percent:.1f}%')
        self.bar.setValue(round(percent))
        self.detail.setText(detail)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PC Care | System Dashboard')
        self.resize(1100, 690)
        self.setMinimumSize(850, 540)
        self.setStyleSheet(STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(18)

        sidebar = QFrame()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(225)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(15, 24, 15, 20)
        nav.setSpacing(8)
        logo = QLabel('✦  PC CARE')
        logo.setObjectName('heading')
        nav.addWidget(logo)
        nav.addSpacing(26)
        self.nav_buttons = {}
        for label in ('Dashboard', 'Junk Cleaner', 'Disk Analyzer', 'Startup Manager', 'Settings'):
            button = QPushButton(label)
            if label == 'Dashboard':
                button.setObjectName('active')
            button.clicked.connect(lambda checked=False, name=label: self.navigate(name))
            self.nav_buttons[label] = button
            nav.addWidget(button)
        nav.addStretch()
        version = QLabel('Version 0.2.0 • Free')
        version.setObjectName('muted')
        nav.addWidget(version)
        outer.addWidget(sidebar)

        content = QWidget()
        column = QVBoxLayout(content)
        column.setContentsMargins(10, 14, 10, 10)
        column.setSpacing(20)
        title = QLabel('System Overview')
        title.setObjectName('title')
        column.addWidget(title)
        subtitle = QLabel('Live usage information • Updates every 2 seconds')
        subtitle.setObjectName('muted')
        column.addWidget(subtitle)
        cards = QHBoxLayout()
        cards.setSpacing(14)
        self.cpu = MetricCard('CPU Usage')
        self.ram = MetricCard('Memory')
        self.disk = MetricCard('System Drive')
        for card in (self.cpu, self.ram, self.disk):
            cards.addWidget(card)
        column.addLayout(cards)
        info = QFrame()
        info.setObjectName('card')
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(22, 22, 22, 22)
        info_title = QLabel('Device Information')
        info_title.setObjectName('heading')
        self.device_info = QLabel('Loading...')
        self.device_info.setObjectName('muted')
        info_layout.addWidget(info_title)
        info_layout.addWidget(self.device_info)
        column.addWidget(info)
        column.addStretch()
        self.pages = QStackedWidget()
        self.pages.addWidget(content)
        self.pages.addWidget(CleanerPage())
        outer.addWidget(self.pages, 1)

        psutil_ready = system_snapshot()
        self.refresh(psutil_ready)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(2000)

    def navigate(self, name):
        if name not in ('Dashboard', 'Junk Cleaner'):
            self.coming_soon(name)
            return
        self.pages.setCurrentIndex(0 if name == 'Dashboard' else 1)
        for label, button in self.nav_buttons.items():
            button.setObjectName('active' if label == name else '')
            button.style().unpolish(button)
            button.style().polish(button)

    def coming_soon(self, name):
        QMessageBox.information(self, name, f'{name} is planned for a future version.')

    def refresh(self, data=None):
        try:
            data = data or system_snapshot()
            self.cpu.update_metric(data['cpu'], 'Current processor load')
            self.ram.update_metric(data['ram'], f"{data['ram_used_gb']:.1f} / {data['ram_total_gb']:.1f} GB used")
            self.disk.update_metric(data['disk'], f"{data['disk_free_gb']:.1f} GB free on {data['drive']}")
            self.device_info.setText(f"Device: {data['device']}    •    OS: {data['os']}")
        except (OSError, ValueError) as exc:
            self.device_info.setText(f'Unable to read system information: {exc}')
