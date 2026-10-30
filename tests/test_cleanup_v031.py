import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.core.safe_cleanup import recycle_selected

class CleanupTests(unittest.TestCase):
    def test_recycles_only_selected_file(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'a.tmp'
            f.write_text('abc')
            st = f.stat()
            with patch('app.core.safe_cleanup.send2trash') as send:
                r = recycle_selected([(str(f), st.st_size, st.st_mtime_ns)], root=Path(d))
            self.assertEqual(r['recycled'], 1)
            send.assert_called_once_with(str(f))

    def test_missing_file_is_not_failure(self):
        with tempfile.TemporaryDirectory() as d:
            r = recycle_selected([(str(Path(d)/'missing.tmp'), 1, 0)], root=Path(d))
            self.assertEqual(r['already_gone'], 1)

    def test_changed_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'a.tmp'; f.write_text('abc')
            with patch('app.core.safe_cleanup.send2trash') as send:
                r = recycle_selected([(str(f), 1, 0)], root=Path(d))
            self.assertEqual(r['changed'], 1)
            send.assert_not_called()

    def test_locked_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / 'a.tmp'; f.write_text('abc'); st = f.stat()
            exc = OSError(32, 'file in use'); exc.winerror = 32
            with patch('app.core.safe_cleanup.send2trash', side_effect=exc):
                r = recycle_selected([(str(f), st.st_size, st.st_mtime_ns)], root=Path(d))
            self.assertEqual(r['skipped_locked'], 1)

if __name__ == '__main__':
    unittest.main()
