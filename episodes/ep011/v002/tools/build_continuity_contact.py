#!/usr/bin/env python3
"""Build the full 44-shot continuity contact sheet, only after every frame is approved."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
plan = json.loads((ROOT / 'storyboard.json').read_text())
shots = plan['shots']
pending = [s['id'] for s in shots if s.get('image_status') != 'generated_continuity_reviewed']
if pending:
    raise SystemExit(f"Not render-ready; image review is incomplete for shots: {pending}")
cols, cell_w, image_h, label_h = 4, 300, 533, 50
rows = (len(shots) + cols - 1) // cols
sheet = Image.new('RGB', (cols * cell_w, rows * (image_h + label_h)), 'white')
draw = ImageDraw.Draw(sheet)
for i, shot in enumerate(shots):
    image_path = ROOT / shot['image']
    if not image_path.is_file():
        raise SystemExit(f"Missing shot image {shot['id']}: {image_path}")
    image = Image.open(image_path).convert('RGB').resize((cell_w, image_h), Image.Resampling.LANCZOS)
    x, y = (i % cols) * cell_w, (i // cols) * (image_h + label_h)
    sheet.paste(image, (x, y + label_h))
    title = str(shot.get('title', ''))[:18]
    draw.text((x + 8, y + 5), f"{shot['id']:02d}  {title}", fill='black')
out = ROOT / 'checks' / 'storyboard_contact.jpg'
out.parent.mkdir(parents=True, exist_ok=True)
sheet.save(out, quality=92)
print(out)
