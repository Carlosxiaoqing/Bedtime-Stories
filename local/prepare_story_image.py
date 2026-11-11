#!/usr/bin/env python3
"""Build one shot's image prompt from its locked source and verified references."""
import argparse
import json
from pathlib import Path

from character_references import ROOT, resolve


def prepare(output, shot_id):
    output = output.resolve()
    plan = json.loads((output / 'storyboard.json').read_text())
    if not plan.get('actual_audio_measured'):
        raise ValueError('先按真实音频锁定分镜再出剧情图')
    shot = next(s for s in plan['shots'] if s['id'] == shot_id)
    refs = resolve(shot['characters'], shot['outfits'])
    paths = list(refs['referenced_image_paths'])
    labels = []
    for character in refs['characters']:
        for path in character['identity_paths']:
            labels.append(f"Input {paths.index(path)+1}: identity for {character['name']} ({character['id']}), preserve exactly: {character['identity_anchors']}")
        if character['outfit']:
            for item in character['outfit']['files']:
                path = str((ROOT / item['path']).resolve())
                labels.append(f"Input {paths.index(path)+1}: clothing only for {character['name']}: {character['outfit']['description']}")
    if plan['episode'] != 'ep004':
        # New episodes provide an explicit scene anchor. Never infer another
        # episode's bedroom or pose from the numeric shot index.
        anchor = shot.get('environment_reference')
        scene = output / anchor if anchor else None
        if scene is not None and not scene.is_file():
            raise FileNotFoundError(f'本镜环境参考不存在：{scene}')
    elif shot_id <= 19 or shot_id in (30, 35):
        scene = output / ('images/shot_03.png' if (output / 'images/shot_03.png').exists() and shot_id != 3 else 'cover_base.png')
        if shot_id in (18, 19) and (output / 'images/shot_17.png').exists():
            scene = output / 'images/shot_17.png'
        if shot_id == 35 and (output / 'images/shot_19.png').exists():
            scene = output / 'images/shot_19.png'
    elif shot_id == 20:
        scene = output / 'images/shot_21.png'
    else:
        scene = output / 'images/shot_21.png'
        if not scene.exists() or shot_id == 21:
            scene = ROOT / 'episodes/ep001/v005/images/shot_01.png'
    if scene is not None and len(paths) < 5:
        if not scene.is_file():
            raise FileNotFoundError(f'环境参考不存在：{scene}')
        paths.append(str(scene.resolve()))
        labels.append(f"Input {len(paths)}: environment layout / watercolor style ONLY. Keep the geography and furnishings, but draw ONLY the requested people and props for this shot, never copy unwanted actors. This is not an image to reuse as the output.")
    names = ', '.join(c['name'] + ' (' + c['id'] + ')' for c in refs['characters']) or 'NONE; no animals or people visible'
    ratios = {'pipi': 1.0, 'lili': .85, 'tuantuan': .9, 'goat_teacher': 1.65}
    scale = 'Standing body-height ratios (not ear or tail tips): ' + ', '.join(f"{c['name']} {ratios[c['id']]}" for c in refs['characters'] if c['id'] in ratios) + '. ' if refs['characters'] else ''
    day = 'pipi' in shot['characters'] and shot['outfits'].get('pipi') == 'day_v001'
    sleep = 'pipi' in shot['characters'] and shot['outfits'].get('pipi') == 'sleep_v001'
    wardrobe = ('Pipi wears ONLY the LEFT daytime outfit from the wardrobe sheet: dusty blue overalls, oatmeal shirt, blue cloth shoes, small yellow backpack. No star cap in daytime. ' if day else '')
    wardrobe += ('Pipi wears ONLY the RIGHT bedtime star cap, navy with pale yellow stars and yellow pompom. No overalls, raincoat, backpack or shoes in bed. Yellow blanket and orange carrot toy with dark green leaves are scene props, not identity changes. ' if sleep else '')
    wardrobe += 'Lili wears ONLY the sage-gray vest, NO SCARF of any color, no neckerchief, no hat. His snack bag is a pale oatmeal rounded FLAP shoulder satchel with one wooden button and one shoulder strap, the same as the cover, NOT a drawstring sack. ' if 'lili' in shot['characters'] else ''
    wardrobe += 'Tuantuan wears the short dark ochre/rust scarf. ' if 'tuantuan' in shot['characters'] else ''
    wardrobe += 'The goat teacher wears the sage cardigan, oatmeal shirt and brown trousers. ' if 'goat_teacher' in shot['characters'] else ''
    states = {
        12: 'BOTH friends are SITTING directly on the grass, bottoms touching ground and legs relaxed forward, not standing. Empty paws before biscuits are opened. One yellow backpack and one pale flap satchel sit BESIDE them, not worn.',
        15: 'BOTH friends remain SITTING on the grass, viewed from a rear three-quarter angle, quietly looking into the valley. They are not standing. Exactly one yellow backpack and one pale satchel, placed beside them; no duplicate bags.',
        16: 'Pipi and Lili are SITTING on the grass. The adult goat teacher kneels or stoops next to them and gently touches one of Pipi’s drooping ears. Exactly THREE animals. One bag per child, resting beside them. Lili has NO scarf.',
        20: 'Pipi sits on a low stool washing BARE FEET at a shallow wooden basin. His blue cloth shoes are OFF, together beside the basin. Still daytime overalls and shirt. No star cap, no backpack worn.',
        23: 'The raised yellow FABRIC mound above Pipi’s feet is the key object, positioned in the upper-middle of the image so subtitles will not hide it. Carrot toy stays by the pillow, not yet picked up. No real grass in bed.',
        24: 'There is exactly ONE orange carrot plush toy in the entire image, now HUGGED in Pipi’s paws, not another copy at the pillow. A small yellow blanket mound remains above the covered feet.',
        25: 'Exactly ONE carrot plush is now sitting on the MID-SLOPE of the raised yellow blanket mound, NOT held at the chest and NOT duplicated by the pillow. Pipi gently steadies it with one paw. Keep the mound and toy above the bottom subtitle area.',
        26: 'A NEW SIDE VIEW from near the foot of the bed, NOT the same frontal pillow portrait: Pipi is in the upper-left background; the outline of his extended covered feet and LOWER yellow blanket mound is in the upper-middle foreground. ONE carrot plush stays resting on the fabric. Do not duplicate it or put it at the chest.',
        27: 'CLOSE-UP from the SIDE of the bed: the yellow blanket is now FLAT and relaxed, no mound. ONE carrot plush lies on the flat fabric, not in Pipi’s paws. Show only the nearby paws/arms and a small partial glimpse of Pipi, not another full frontal portrait. Fabric remains yellow cloth, never grass.',
        28: 'A CLOSE DETAIL view of one paw gently opening a FOLDED CORNER of the same yellow blanket at the wooden bed edge. The paw and cloth are the main subject, not the full face or window. ONE carrot plush nearby. Position the folded cloth corner and paw in the upper-middle, not behind subtitles.',
        29: 'NO characters, NO animals: a close environment view of warm lamp and leaf-curtained wooden window. Trees outside in blue night. No prominent moon.',
        31: 'NEW SIDE PROFILE view of Pipi comfortably reclining in bed. ONE carrot plush lies beside him, not yet hugged. Blanket lies flat. Do not repeat the frontal upright portrait.',
        32: 'CLOSE facial/pillow view of Pipi comfortably reclining, long ears spread softly on the pillow, hugging exactly ONE carrot plush in his arms. Crop most of the large window and bed frame; focus on face, ears and toy. No duplicate toy anywhere.',
        33: 'NEW WIDER ROOM view from the doorway: Pipi is comfortably reclining under the flat yellow blanket, holding ONE carrot plush. Yellow backpack and blue cloth shoes are stored near the doorway, not worn in bed. Show space around the bed, not another tight portrait.',
        34: 'NEW SIDE VIEW showing the long wooden bed and ONE reclining Pipi supported by pillow and mattress, covered feet stretched flat. ONE carrot plush in his arm. Do not repeat the frontal upright portrait. Entire story action remains above the subtitle zone.',
        35: 'Exterior of the familiar red-roof wooden cottage at night, warm window light, quiet blue-gray trees and same rounded grassy hill. NO visible animals or people. No text.',
    }
    constraints = shot.get('visual_constraints') or (states.get(shot_id) if plan['episode'] == 'ep004' else None) or 'Follow the specified moment exactly; never add extra actors, garments or duplicate props.'
    prompt = (
        'Use case: illustration-story. Asset type: ONE original full-bleed vertical 9:16 watercolor story illustration for one locked narration shot. '
        'Use every input according to its explicitly labelled role; preserve the existing named identities, not just their species. '
        + ' '.join(labels) + '\n'
        + f'Visible characters: {names}. Exact total number of visible characters: {len(shot["characters"])}. Do not draw extra background animals. '
        + scale
        + wardrobe
        + f"Scene continuity: {shot['setting'].split('；皮皮')[0]}\n"
        + f"The SINGLE visual moment and framing: {shot['action']}\n"
        + f"Mandatory pose/prop state (overrides neutral model-sheet poses): {constraints}\n"
        + 'Style: hand-painted gentle watercolor on fine warm paper, muted natural hues, soft edges and rounded shapes, quiet storybook mood, no glossy 3D or photorealism. Daylight scenes use soft greens and warm daylight, not bedroom amber tint. Night scenes use soft warm lamplight and muted gray-blue windows. '
        + 'Composition: full-bleed vertical 9:16. Keep all important faces, hands, feet, biscuits, fabric folds and other story actions in the upper 68% of the image. Bottom 32% is low-detail negative space for later subtitles, with no crucial objects there. Make the specified story state visually understandable. '
        + 'Text: NONE. No words, labels, subtitles, numbers, logos, watermark, speech bubbles, panels, frames or collage. Do not reproduce model sheets, multiple versions of a character, or wardrobe lineups. Each named character appears exactly once. This is a new single coherent scene, not a copy of the references. No motion streaks or implied camera zoom. '
        + 'Never turn a metaphor into a real transformation: yellow blankets remain fabric, imagined grassy softness is not actual grass growing in bed. No new story events. '
    )
    payload = {'id': shot_id, 'title': shot['title'], 'destination': str(output / shot['image']),
               'prompt': prompt, 'reference_inputs': paths, 'characters': shot['characters'],
               'outfits': shot['outfits'], 'source_ranges': shot['source_ranges'],
               'timing': {'start_s': shot['actual_start_s'], 'end_s': shot['actual_end_s']}}
    (output / 'prompts' / f'shot_{shot_id:02}.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    (output / shot['reference_manifest']).write_text(json.dumps(refs, ensure_ascii=False, indent=2) + '\n')
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--shot', type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output_dir, args.shot), ensure_ascii=False))


if __name__ == '__main__':
    main()
