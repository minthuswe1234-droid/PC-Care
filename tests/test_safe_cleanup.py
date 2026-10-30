import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.core.safe_cleanup import recycle_selected, validate_candidate

class CleanupTests(unittest.TestCase):
    def test_outside_temp_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaises(ValueError):
                validate_candidate(root.parent / 'other.txt', 0, 0, root=root)

    def test_changed_file_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / 'x.txt'
            file.write_text('hello')
            with self.assertRaises(ValueError):
                validate_candidate(file, 99, 0, root=root)

    def test_selected_file_recycled_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / 'x.txt'
            other = root / 'y.txt'
            file.write_text('hello')
            other.write_text('stay')
            stat = file.stat()
            with patch('app.core.safe_cleanup.send2trash') as recycle:
                result = recycle_selected([(str(file), stat.st_size, stat.st_mtime_ns)], root=root)
            recycle.assert_called_once_with(str(file))
            self.assertEqual(result['recycled'], 1)
            self.assertTrue(other.exists())
