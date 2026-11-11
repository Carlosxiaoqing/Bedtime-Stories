"""Exercise date rollover, time-zone and overwrite rules without a video render."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run

class OutputRules(unittest.TestCase):
    def test_date_rollover(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(run,'ROOT',Path(temp)):
            a=run.new_output_dir(datetime(2026,11,10,23,59,59,tzinfo=run.CST),'render')
            b=run.new_output_dir(datetime(2026,11,11,0,0,0,tzinfo=run.CST),'render')
            self.assertEqual(a.parent.name,'2026-11-10')
            self.assertEqual(b.parent.name,'2026-11-11')
            self.assertEqual(b.parent.parent.name,'本地复现')
            self.assertEqual(b.parent.parent.parent.name,'ep001')
            self.assertFalse((Path(temp)/'Outputs').exists())
    def test_repeat_preserves_previous_run(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(run,'ROOT',Path(temp)):
            now=datetime(2026,11,10,12,0,tzinfo=run.CST)
            a=run.new_output_dir(now,'render'); (a/'ep001.mp4').write_bytes(b'previous')
            b=run.new_output_dir(now,'render')
            self.assertNotEqual(a,b)
            self.assertEqual((a/'ep001.mp4').read_bytes(),b'previous')
    def test_uses_beijing_day(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(run,'ROOT',Path(temp)):
            output=run.new_output_dir(datetime(2026,11,10,16,0,tzinfo=timezone.utc),'render')
            self.assertEqual(output.parent.name,'2026-11-11')

if __name__=='__main__': unittest.main()
