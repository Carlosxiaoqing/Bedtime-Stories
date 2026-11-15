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
            shutil.copy2(ROOT/'PROJECT_STATE.json', repo/'PROJECT_STATE.json')
            source = Path(json.loads((ROOT/'PROJECT_STATE.json').read_text())['script_json_directory'])
            shutil.copytree(ROOT/source, repo/source)
            registry = Path('03_素材与参数/用户长稿v4角色图库.json')
            (repo/registry).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT/registry, repo/registry)
            shutil.copy2(ROOT/'03_素材与参数/封面与字幕参数.json', repo/'03_素材与参数/封面与字幕参数.json')
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
            subprocess.run([sys.executable, str(repo/'local/render_long_episode.py'), '--output-dir', str(work), '--preview-seconds', '2', '--legacy-cover'], check=True, capture_output=True, text=True, cwd=repo)
            movie = work/'ep099_preview2.mp4'
            info = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(movie)]))
            video = next(s for s in info['streams'] if s['codec_type'] == 'video')
            self.assertEqual(int(video['nb_frames']), 50)
            self.assertEqual(video['avg_frame_rate'], '25/1')
            self.assertFalse((work/'ep004_preview2.mp4').exists())
            self.assertFalse((repo/'Outputs').exists())
            # Exercise the new default path in the same disposable fixture.
            # The retained media is only a decoder/layout fixture, not new art.
            for name in ('cover.png', 'cover.svg', 'cover-title.txt'):
                (work/name).unlink(missing_ok=True)
            (work/'script.snapshot.json').write_text(json.dumps(dict(id='ep099', script_version='v5',
                narration_paragraphs=[dict(id='p001', text='技术测试，不作为新剧本。')]), ensure_ascii=False))
            cover = dict(template='bedtime-cover-v3', episode='ep099', title='皮皮给刺猬铺坐垫',
                         title_lines=['皮皮给刺猬', '铺坐垫'], scene='技术测试', dominant_color='测试',
                         pipi_front_facing=True, pipi_pose='测试', pipi_expression='测试', key_props=['测试'],
                         event_description='仅排版与渲染集成测试', source_paragraph_ids=['p001'],
                         reference_inputs=[str(work/'cover_base.png')])
            (work/'cover-plan.json').write_text(json.dumps(cover, ensure_ascii=False))
            subprocess.run([sys.executable, str(repo/'local/render_long_episode.py'), '--output-dir', str(work),
                            '--preview-seconds', '1'], check=True, capture_output=True, text=True, cwd=repo)
            metadata = json.loads((work/'project_preview1.json').read_text())
            self.assertEqual(metadata['cover_template'], 'bedtime-cover-v3')
            self.assertEqual(metadata['cover_title'], cover['title'])
            self.assertEqual(metadata['frames'], 25)
            self.assertTrue((work/'cover-render.json').is_file())
            self.assertFalse((repo/'Outputs').exists())


if __name__ == '__main__':
    unittest.main()
