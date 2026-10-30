import tempfile
import unittest
from pathlib import Path
from app.core.disk_analyzer import analyze_folder
from app.core.scan_history import save_scan, recent_scans

class DiskAnalyzerTests(unittest.TestCase):
    def test_sizes_and_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'docs').mkdir()
            (root / 'docs' / 'one.txt').write_bytes(b'1234')
            (root / 'two.txt').write_bytes(b'123456')
            result = analyze_folder(root)
            self.assertEqual(result['files'], 2)
            self.assertEqual(result['bytes'], 10)
            self.assertIn(('docs', 4), result['folders'])

    def test_limit_and_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'one').write_bytes(b'x')
            result = analyze_folder(root, limit=1)
            self.assertTrue(result['partial'])
            db = root / 'history.sqlite3'
            save_scan(result, db=db)
            self.assertEqual(recent_scans(db=db)[0][2], 1)

    def test_cancel(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = analyze_folder(tmp, cancelled=lambda: True)
            self.assertTrue(result['partial'])

if __name__ == '__main__':
    unittest.main()
