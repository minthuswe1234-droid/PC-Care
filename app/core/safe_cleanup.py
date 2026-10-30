"""Conservative user-temp cleanup: selected files only, sent to Recycle Bin."""
from pathlib import Path
from send2trash import send2trash
from app.core.junk_scanner import user_temp_directory


def validate_candidate(path, expected_size, expected_mtime_ns, root=None):
    root = (root or user_temp_directory()).resolve(strict=True)
    target = Path(path)
    # Never follow symlinks in any component, including the temp root descendants.
    if not target.is_absolute() or target == root or root not in target.parents:
        raise ValueError('File is outside the allowed temp directory')
    current = root
    for component in target.relative_to(root).parts:
        current = current / component
        if current.is_symlink():
            raise ValueError('Symbolic links are not allowed')
    stat = target.stat(follow_symlinks=False)
    if not target.is_file() or stat.st_size != expected_size or stat.st_mtime_ns != expected_mtime_ns:
        raise ValueError('File changed since scan; rescan before cleaning')
    return target


def recycle_selected(items, root=None):
    """items: iterable of (absolute_path, size, mtime_ns). No permanent deletion."""
    summary = {'recycled': 0, 'bytes': 0, 'failed': [], 'skipped_locked': 0, 'already_gone': 0, 'changed': 0}
    for path, size, mtime_ns in items:
        try:
            target = validate_candidate(path, size, mtime_ns, root=root)
            send2trash(str(target))
            summary['recycled'] += 1
            summary['bytes'] += size
        except FileNotFoundError:
            summary['already_gone'] += 1
        except PermissionError as exc:
            summary['skipped_locked'] += 1
        except ValueError as exc:
            if str(exc) == 'File changed since scan; rescan before cleaning':
                summary['changed'] += 1
            else:
                summary['failed'].append((str(path), str(exc)))
        except OSError as exc:
            if getattr(exc, 'winerror', None) in (32, 33):
                summary['skipped_locked'] += 1
            elif getattr(exc, 'winerror', None) in (2, 3):
                summary['already_gone'] += 1
            else:
                summary['failed'].append((str(path), str(exc)))
        except RuntimeError as exc:
            summary['failed'].append((str(path), str(exc)))
    return summary
