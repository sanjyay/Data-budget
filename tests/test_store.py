import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from store import Store

STATE = {'version': 1, 'profiles': {}}


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.store = Store(self.base)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_roundtrip_and_private_modes(self):
        self.assertIsNone(self.store.load())
        self.store.save(STATE)
        self.assertEqual(self.store.load(), STATE)
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.store.path / 'state.json').stat().st_mode & 0o777, 0o600)

    def test_single_owner_lock(self):
        with self.assertRaisesRegex(ValueError, 'already running'):
            Store(self.base)
        self.store.close()
        other = Store(self.base)
        other.close()

    def test_symlink_state_rejected(self):
        target = self.base / 'unrelated'
        target.write_text('untouched')
        (self.store.path / 'state.json').symlink_to(target)
        with self.assertRaises(OSError):
            self.store.load()
        self.assertEqual(target.read_text(), 'untouched')

    def test_corruption_preserved(self):
        self.store.save(STATE)
        path = self.store.path / 'state.json'
        path.write_text('{broken')
        with self.assertRaises(ValueError):
            self.store.load()
        self.assertEqual(path.read_text(), '{broken')

    def test_failed_replace_keeps_old_file_and_cleans_temporary(self):
        self.store.save(STATE)
        with patch('store.os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.store.save(STATE)
        self.assertEqual(self.store.load(), STATE)
        self.assertEqual(sorted(p.name for p in self.store.path.iterdir()), ['lock', 'state.json'])

    def test_shared_permissions_rejected(self):
        self.store.save(STATE)
        (self.store.path / 'state.json').chmod(0o644)
        with self.assertRaises(ValueError):
            self.store.load()

    def test_fifo_rejected_without_blocking(self):
        os.mkfifo(self.store.path / 'state.json', 0o600)
        with self.assertRaises(ValueError):
            self.store.load()

    def test_relative_root_rejected(self):
        with self.assertRaises(ValueError):
            Store('relative')

    def test_directory_symlink_rejected(self):
        self.store.close()
        os.rename(self.base / 'hotspot-budget', self.base / 'real')
        (self.base / 'hotspot-budget').symlink_to(self.base / 'real', target_is_directory=True)
        with self.assertRaises(OSError):
            Store(self.base)
