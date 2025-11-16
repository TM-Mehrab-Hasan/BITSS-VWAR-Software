import unittest
import os
from datetime import datetime, timedelta
from Scanning.scheduled_scan import ScanScheduleConfig, should_run_interval, is_due_daily, is_due_weekly, ScheduledScanRunner

class TestScheduledScanLogic(unittest.TestCase):
    def test_interval_due_first_run(self):
        now = datetime(2025,1,1,12,0)
        self.assertTrue(should_run_interval(now, None, 60))

    def test_interval_not_due(self):
        now = datetime(2025,1,1,13,0)
        last = (now - timedelta(minutes=30)).isoformat()
        self.assertFalse(should_run_interval(now, last, 60))

    def test_interval_due_after_elapsed(self):
        now = datetime(2025,1,1,13,0)
        last = (now - timedelta(minutes=61)).isoformat()
        self.assertTrue(should_run_interval(now, last, 60))

    def test_daily_due_first(self):
        now = datetime(2025,1,2,10,15)
        cfg = ScanScheduleConfig(enabled=True,time="10:15",paths=[],weekdays=[0])
        cfg.frequency='daily'
        self.assertTrue(is_due_daily(now,cfg))

    def test_daily_not_duplicate_same_minute(self):
        now = datetime(2025,1,2,10,15)
        cfg = ScanScheduleConfig(enabled=True,time="10:15",paths=[],weekdays=[0], last_run=now.isoformat())
        cfg.frequency='daily'
        self.assertFalse(is_due_daily(now,cfg))

    def test_weekly_only_selected_weekday(self):
        now = datetime(2025,1,6,9,0) # Monday
        cfg = ScanScheduleConfig(enabled=True,time="09:00",paths=[],weekdays=[0])
        cfg.frequency='weekly'
        self.assertTrue(is_due_weekly(now,cfg))
        # Different day
        other = datetime(2025,1,7,9,0)
        self.assertFalse(is_due_weekly(other,cfg))

    def test_excludes_project_root_from_scheduled_scan(self):
        runner = ScheduledScanRunner()
        # simulate project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        # ensure helper recognizes it as excluded
        self.assertTrue(runner._is_excluded(project_root))
        # Any file inside should also be excluded
        some_internal = os.path.join(project_root, 'assets', 'yara', 'rule.yar')
        self.assertTrue(runner._is_excluded(some_internal))

if __name__ == '__main__':
    unittest.main()
