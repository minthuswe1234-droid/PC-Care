import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.core.junk_scanner import scan_temp


class JunkScannerTests(unittest.TestCase):
    def test_counts_files_without_following_symlinks(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'one.txt').write_bytes(b'1234')
            (root / 'nested').mkdir()
            (root / 'nested' / 'two.txt').write_bytes(b'abc')
            with patch('app.core.junk_scanner.user_temp_directory', return_value=root):
                result = scan_temp()
            self.assertEqual(result['files'], 2)
            self.assertEqual(result['bytes'], 7)
            self.assertFalse(result['partial'])

    def test_cancel(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('app.core.junk_scanner.user_temp_directory', return_value=Path(folder)):
                result = scan_temp(cancelled=lambda: True)
            self.assertTrue(result['partial'])
