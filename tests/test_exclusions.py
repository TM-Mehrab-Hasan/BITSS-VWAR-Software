import os
import unittest
from utils.exclusions import is_excluded_path, is_temp_like_file, get_base_dir

class TestExclusions(unittest.TestCase):
    def test_temp_extensions(self):
        for name in [
            'file.tmp','file.part','file.crdownload','file.swp','file.bak','file.lock','file.log'
        ]:
            self.assertTrue(is_temp_like_file(name), f"Expected temp-like: {name}")

    def test_temp_prefixes_and_names(self):
        for name in ['~$doc.docx','._hidden','thumbs.db','.ds_store']:
            self.assertTrue(is_temp_like_file(name), f"Expected temp-like: {name}")

    def test_internal_root_excluded(self):
        base = get_base_dir()
        excluded, reason = is_excluded_path(base)
        self.assertTrue(excluded)
        self.assertEqual(reason, 'INTERNAL')

    def test_temp_root_excluded(self):
        import tempfile
        tempdir = tempfile.gettempdir()
        excluded, reason = is_excluded_path(tempdir)
        self.assertTrue(excluded)
        self.assertEqual(reason, 'TEMP_ROOT')

if __name__ == '__main__':
    unittest.main()
