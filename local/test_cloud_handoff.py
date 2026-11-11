"""Exercise portable sources and episode-specific behavior in a disposable copy."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CloudHandoff(unittest.TestCase):
    def test_portable_checkout_and_generic_episode(self):
        with tempfile.TemporaryDirectory(prefix='bedtime-portable-') as folder:
            repo = Path(folder).resolve()/'checkout'
            shutil.copytree(ROOT/'local', repo/'local', ignore=shutil.ignore_patterns('__pycache__'))
            source = Path('02_100集剧本/用户长稿v4/结构化JSON')
            shutil.copytree(ROOT/source, repo/source)
            registry = Path('03_素材与参数/用户长稿v4角色图库.json')
            (repo/registry).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/registry, repo/registry)
            def copy_registered(value):
                if isinstance(value, dict):
                    if 'path' in value and 'sha256' in value:
                        path = Path(value['path'])
                        if not path.is_absolute() and (ROOT/path).is_file():
                            (repo/path).parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(ROOT/path, repo/path)
                    for v in value.values():
                        copy_registered(v)
                elif isinstance(value, list):
                    for v in value:
                        copy_registered(v)
            copy_registered(json.loads((ROOT/registry).read_text()))
            relative = Path('episodes/ep004/v001')
            old, work = ROOT/relative, repo/relative
            work.mkdir(parents=True)
            names = ('storyboard.json', 'script.snapshot.json', 'cover-title.txt', 'cover.png',
                     'cover_base.png', '用户验收记录.json', 'audio/voice.wav', 'mix.wav',
                     'episode.ass', 'subtitles.ruby.json')
            plan = json.loads((old/'storyboard.json').read_text())
            for name in (*names, *(s['image'] for s in plan['shots'])):
                (work/name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old/name, work/name)
            result = subprocess.run([sys.executable, str(repo/'local/cloud_preflight.py')], check=True, capture_output=True, text=True, cwd=repo)
            self.assertEqual(json.loads(result.stdout)['offline_preflight'], 'passed')
            # A synthetic fixture proves that shot 28 of a new episode does not
            # inherit episode 004's folded blanket and bedroom instructions.
            shot = dict(plan['shots'][27])
            shot.update(id=28, characters=['pipi'], outfits={'pipi': 'day_v001'},
                        setting='林间小路', action='皮皮举起一只爪子打招呼',
                        visual_constraints='Pipi waves one paw.', reference_manifest='references/shot_28.json')
            fixture = dict(plan, episode='ep099', shots=[shot], shot_count=1)
            (work/'storyboard.json').write_text(json.dumps(fixture, ensure_ascii=False))
            (work/'references').mkdir(exist_ok=True)
            (work/'prompts').mkdir(exist_ok=True)
            result = subprocess.run([sys.executable, str(repo/'local/prepare_story_image.py'), '--output-dir', str(work), '--shot', '28'], check=True, capture_output=True, text=True, cwd=repo)
            payload = json.loads(result.stdout)
            self.assertIn('Pipi waves one paw.', payload['prompt'])
            self.assertNotIn('FOLDED CORNER', payload['prompt'])
            self.assertEqual(len(payload['reference_inputs']), 2)
            self.assertTrue(all(Path(p).is_relative_to(repo) for p in payload['reference_inputs']))
            # Render two seconds only in this temp directory, using real retained
            # episode 004 media as a technical fixture, never as a new episode.
            shot = dict(plan['shots'][0], actual_start_s=0., actual_end_s=2.,
                        visible_start_s=0., visible_end_s=2., visible_duration_s=2.)
            fixture = dict(plan, episode='ep099', cover_title='林间问好', shots=[shot],
                           shot_count=1, total_duration_s=2., max_visible_duration_s=2.)
            (work/'storyboard.json').write_text(json.dumps(fixture, ensure_ascii=False))
            (work/'fonts').mkdir(exist_ok=True)
            subprocess.run([sys.executable, str(repo/'local/render_long_episode.py'), '--output-dir', str(work), '--preview-seconds', '2'], check=True, capture_output=True, text=True, cwd=repo)
            movie = work/'ep099_preview2.mp4'
            info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(movie)]))
            video = next(s for s in info['streams'] if s['codec_type'] == 'video')
            self.assertEqual(int(video['nb_frames']), 50)
            self.assertEqual(video['avg_frame_rate'], '25/1')
            self.assertFalse((work/'ep004_preview2.mp4').exists())
            self.assertFalse((repo/'Outputs').exists())


if __name__ == '__main__':
    unittest.main()
