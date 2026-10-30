"""Read-only scanner for the current user's Windows temporary directory."""
import os
import tempfile
from pathlib import Path


def user_temp_directory():
    """Return only the OS-provided user temp directory."""
    return Path(tempfile.gettempdir()).resolve()


def scan_temp(progress=None, cancelled=None, limit=200_000):
    """Enumerate regular files without following directory symlinks.

    Returns a summary and a bounded sample of paths. Never deletes anything.
    Errors (including inaccessible files) are counted, not fatal.
    """
    root = user_temp_directory()
    total_bytes = 0
    files = 0
    errors = 0
    samples = []
    scanned_dirs = 0
    stopped = False
    stack = [root]
    while stack:
        if cancelled and cancelled():
            stopped = True
            break
        folder = stack.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if cancelled and cancelled():
                        stopped = True
                        break
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            size = entry.stat(follow_symlinks=False).st_size
                            total_bytes += size
                            files += 1
                            if len(samples) < 1000:
                                samples.append((entry.path, size))
                            if files >= limit:
                                stopped = True
                                break
                    except (OSError, PermissionError):
                        errors += 1
        except (OSError, PermissionError):
            errors += 1
        scanned_dirs += 1
        if progress and scanned_dirs % 10 == 0:
            progress(files, total_bytes)
        if stopped:
            break
    if progress:
        progress(files, total_bytes)
    return {'root': str(root), 'files': files, 'bytes': total_bytes,
            'errors': errors, 'samples': samples, 'partial': stopped}
