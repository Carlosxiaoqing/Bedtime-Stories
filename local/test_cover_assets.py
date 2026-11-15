"""Cover layout, title consistency, and protection of existing artifacts."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from cover_assets import load_cover_plan, render_cover, validate_cover_outputs, validate_publish_titles


class CoverAssets(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bedtime-cover-check-')
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        Image.new('RGB', (1080, 1920), '#799786').save(self.out / 'cover_base.png')
        # Synthetic technical fixture; this is not an episode production.
        self.plan = dict(template='bedtime-cover-v3', episode='ep099', title='皮皮给刺猬铺坐垫',
                         title_lines=['皮皮给刺猬', '铺坐垫'], scene='测试场景', dominant_color='测试绿',
                         pipi_front_facing=True, pipi_pose='测试动作', pipi_expression='测试表情',
                         event_description='技术测试', key_props=['测试坐垫'], source_paragraph_ids=['p001'],
                         reference_inputs=[str(self.out / 'cover_base.png')])
        (self.out / 'script.snapshot.json').write_text(json.dumps(dict(script_version='v5', id='ep099',
            narration_paragraphs=[dict(id='p001', text='技术测试，不作为剧本。')]), ensure_ascii=False))
        self.save_plan()

    def save_plan(self):
        (self.out / 'cover-plan.json').write_text(json.dumps(self.plan, ensure_ascii=False))

    def copy_text(self, title):
        return '\n\n'.join(f'## {platform}\n\n**标题：** {title}\n\n**正文：** 测试\n\n#睡前故事'
                            for platform in ('抖音', '小红书', '微信视频号'))

    def test_six_to_ten_character_titles_fit_without_clipping(self):
        for lines in (['皮皮给', '风铃系结'], ['皮皮把故事', '留到明天'],
                      ['皮皮给刺猬', '铺坐垫'], ['皮皮和小鹿', '给风铃系结'], ['皮皮听', '风铃声']):
            with self.subTest(lines=lines):
                self.plan.update(title=''.join(lines), title_lines=lines)
                self.save_plan()
                for name in ('cover.png', 'cover.svg', 'cover-title.txt', 'cover-render.json'):
                    (self.out / name).unlink(missing_ok=True)
                report = render_cover(self.out)
                with Image.open(self.out / 'cover.png') as cover_image:
                    self.assertEqual(cover_image.size, (1080, 1920))
                self.assertEqual(report['layout_bounds'], 'passed')
                self.assertEqual(report['pipi_front_face_review'], 'pending')
                self.assertEqual((self.out / 'cover-title.txt').read_text().strip(), self.plan['title'])
                self.assertEqual(render_cover(self.out), report)
                self.assertEqual(validate_cover_outputs(self.out), report)
                self.plan['differentiation_review'] = {'status': 'reviewed_in_fixture'}
                self.save_plan()
                self.assertEqual(validate_cover_outputs(self.out), report)

    def test_reject_short_old_title_and_inconsistent_line_breaks(self):
        for title, lines in [('晚安书签', ['晚安', '书签']),
                             ('皮皮给刺猬铺坐垫', ['皮皮给', '刺猬铺垫']),
                             ('皮皮和小松鼠一起去捡果子', ['皮皮和小松鼠', '一起去捡果子'])]:
            with self.subTest(title=title):
                self.plan.update(title=title, title_lines=lines)
                self.save_plan()
                with self.assertRaises(ValueError):
                    load_cover_plan(self.out)

    def test_title_mismatch_or_missing_platform_is_rejected(self):
        path = self.out / '发布文案.md'
        text = self.copy_text(self.plan['title'])
        path.write_text(text)
        self.assertEqual(len(validate_publish_titles(path, self.plan['title'])), 3)
        for bad in (text.replace(self.plan['title'], '晚安书签', 1),
                    text.split('## 微信视频号')[0]):
            path.write_text(bad)
            with self.assertRaises(ValueError):
                validate_publish_titles(path, self.plan['title'])

    def test_changed_input_or_untracked_cover_never_overwrites_existing(self):
        render_cover(self.out)
        path = self.out / 'cover.png'
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        Image.new('RGB', (1080, 1920), '#182232').save(self.out / 'cover_base.png')
        with self.assertRaises(FileExistsError):
            render_cover(self.out)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)
        with self.assertRaises(ValueError):
            validate_cover_outputs(self.out)
        (self.out / 'cover-render.json').unlink()
        with self.assertRaises(FileExistsError):
            render_cover(self.out)


if __name__ == '__main__':
    unittest.main()
