import os
from pathlib import Path
import platform
import psutil


def system_snapshot():
    drive = Path(os.environ.get('SystemDrive', 'C:') + '\\') if os.name == 'nt' else Path.home()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage(str(drive))
    return {
        'cpu': psutil.cpu_percent(interval=None),
        'ram': memory.percent,
        'disk': disk.percent,
        'ram_used_gb': memory.used / (1024 ** 3),
        'ram_total_gb': memory.total / (1024 ** 3),
        'disk_free_gb': disk.free / (1024 ** 3),
        'drive': str(drive),
        'os': f'{platform.system()} {platform.release()}',
        'device': platform.node() or 'Windows PC',
    }
