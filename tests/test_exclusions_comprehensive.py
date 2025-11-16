import os
import sys
import unittest
from utils.exclusions import is_excluded_path, get_base_dir, get_internal_exclude_roots

class TestComprehensiveExclusions(unittest.TestCase):
    """Comprehensive test for all exclusion paths including new additions."""
    
    def setUp(self):
        """Setup test paths based on project structure."""
        self.base_dir = get_base_dir()
        
    def test_project_root_excluded(self):
        """Test that project root is excluded."""
        excluded, reason = is_excluded_path(self.base_dir)
        self.assertTrue(excluded, f"Project root should be excluded: {self.base_dir}")
        self.assertEqual(reason, 'INTERNAL', "Should be marked as INTERNAL")
        print(f"✓ Project root excluded: {self.base_dir}")
    
    def test_dist_folder_excluded(self):
        """Test that dist folder is excluded."""
        dist_path = os.path.join(self.base_dir, 'dist')
        excluded, reason = is_excluded_path(dist_path)
        self.assertTrue(excluded, f"dist folder should be excluded: {dist_path}")
        self.assertEqual(reason, 'INTERNAL')
        print(f"✓ dist/ folder excluded: {dist_path}")
    
    def test_build_folder_excluded(self):
        """Test that build folder is excluded."""
        build_path = os.path.join(self.base_dir, 'build')
        excluded, reason = is_excluded_path(build_path)
        self.assertTrue(excluded, f"build folder should be excluded: {build_path}")
        self.assertEqual(reason, 'INTERNAL')
        print(f"✓ build/ folder excluded: {build_path}")
    
    def test_pycache_excluded(self):
        """Test that __pycache__ is excluded."""
        pycache_path = os.path.join(self.base_dir, '__pycache__')
        excluded, reason = is_excluded_path(pycache_path)
        self.assertTrue(excluded, f"__pycache__ should be excluded: {pycache_path}")
        self.assertEqual(reason, 'INTERNAL')
        print(f"✓ __pycache__/ excluded: {pycache_path}")
    
    def test_git_folder_excluded(self):
        """Test that .git folder is excluded."""
        git_path = os.path.join(self.base_dir, '.git')
        excluded, reason = is_excluded_path(git_path)
        self.assertTrue(excluded, f".git folder should be excluded: {git_path}")
        self.assertEqual(reason, 'INTERNAL')
        print(f"✓ .git/ folder excluded: {git_path}")
    
    def test_venv_excluded(self):
        """Test that .venv folder is excluded."""
        venv_path = os.path.join(self.base_dir, '.venv')
        excluded, reason = is_excluded_path(venv_path)
        self.assertTrue(excluded, f".venv folder should be excluded: {venv_path}")
        self.assertEqual(reason, 'INTERNAL')
        print(f"✓ .venv/ folder excluded: {venv_path}")
    
    def test_vwar_i_excluded(self):
        """Test that VWAR_i installer folder is excluded."""
        vwar_i_path = os.path.join(self.base_dir, 'VWAR_i')
        excluded, reason = is_excluded_path(vwar_i_path)
        self.assertTrue(excluded, f"VWAR_i folder should be excluded: {vwar_i_path}")
        self.assertEqual(reason, 'INTERNAL')
        print(f"✓ VWAR_i/ installer folder excluded: {vwar_i_path}")
    
    def test_yara_folder_excluded(self):
        """Test that assets/yara folder is excluded."""
        yara_path = os.path.join(self.base_dir, 'assets', 'yara')
        excluded, reason = is_excluded_path(yara_path)
        self.assertTrue(excluded, f"assets/yara should be excluded: {yara_path}")
        self.assertEqual(reason, 'INTERNAL')
        print(f"✓ assets/yara/ folder excluded: {yara_path}")
    
    def test_quarantine_excluded(self):
        """Test that quarantine folder is excluded."""
        quarantine_path = os.path.join(self.base_dir, 'quarantine')
        excluded, reason = is_excluded_path(quarantine_path)
        self.assertTrue(excluded, f"quarantine folder should be excluded: {quarantine_path}")
        self.assertEqual(reason, 'INTERNAL')
        print(f"✓ quarantine/ folder excluded: {quarantine_path}")
    
    def test_nested_file_in_excluded_folder(self):
        """Test that files inside excluded folders are also excluded."""
        nested_file = os.path.join(self.base_dir, 'dist', 'VWAR.exe')
        excluded, reason = is_excluded_path(nested_file)
        self.assertTrue(excluded, f"Files in dist/ should be excluded: {nested_file}")
        self.assertEqual(reason, 'INTERNAL')
        print(f"✓ Nested file in dist/ excluded: {nested_file}")
    
    def test_recycle_bin_excluded(self):
        """Test that Recycle Bin paths are excluded."""
        recycle_path = r"C:\$Recycle.Bin\S-1-5-21-123456789\test.txt"
        excluded, reason = is_excluded_path(recycle_path)
        self.assertTrue(excluded, f"Recycle Bin should be excluded: {recycle_path}")
        self.assertEqual(reason, 'RECYCLE_BIN')
        print(f"✓ Recycle Bin excluded: {recycle_path}")
    
    def test_temp_folder_excluded(self):
        """Test that Windows temp folders are excluded."""
        import tempfile
        temp_path = tempfile.gettempdir()
        excluded, reason = is_excluded_path(temp_path)
        self.assertTrue(excluded, f"Temp folder should be excluded: {temp_path}")
        self.assertEqual(reason, 'TEMP_ROOT')
        print(f"✓ Temp folder excluded: {temp_path}")
    
    def test_normal_file_not_excluded(self):
        """Test that normal user files are NOT excluded."""
        # Test a path outside the project directory
        normal_path = r"C:\Users\TestUser\Documents\myfile.txt"
        excluded, reason = is_excluded_path(normal_path)
        self.assertFalse(excluded, f"Normal file should NOT be excluded: {normal_path}")
        self.assertEqual(reason, 'NONE')
        print(f"✓ Normal file NOT excluded: {normal_path}")
    
    def test_all_internal_roots_listed(self):
        """Print all internal exclusion roots for verification."""
        roots = get_internal_exclude_roots()
        print("\n=== All Internal Exclusion Roots ===")
        for root in sorted(roots):
            print(f"  - {root}")
        print(f"Total: {len(roots)} exclusion roots")
        self.assertGreater(len(roots), 0, "Should have at least one exclusion root")

if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
