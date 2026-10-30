"""Read-only, bounded folder analyzer. Does not follow symlinks."""
import os
from pathlib import Path


def analyze_folder(folder, cancelled=None, progress=None, limit=100_000):
    root = Path(folder).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('Choose a directory')
    stack = [root]
    files = 0
    total = 0
    errors = 0
    partial = False
    largest = []
    top_folders = {}
    while stack:
        if cancelled and cancelled():
            partial = True
            break
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    if cancelled and cancelled():
                        partial = True
                        break
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            size = entry.stat(follow_symlinks=False).st_size
                            files += 1
                            total += size
                            relative = Path(entry.path).relative_to(root)
                            group = relative.parts[0] if len(relative.parts) > 1 else '(root files)'
                            top_folders[group] = top_folders.get(group, 0) + size
                            largest.append((size, entry.path))
                            if len(largest) > 30:
                                largest.sort(reverse=True)
                                largest.pop()
                            if files >= limit:
                                partial = True
                                break
                    except OSError:
                        errors += 1
        except OSError:
            errors += 1
        if progress:
            progress(files, total)
        if partial:
            break
    return {'root': str(root), 'files': files, 'bytes': total,
            'errors': errors, 'partial': partial,
            'folders': sorted(top_folders.items(), key=lambda x: x[1], reverse=True)[:30],
            'largest': sorted(largest, reverse=True)}
