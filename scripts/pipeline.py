#!/usr/bin/env python3
"""Daily pipeline: story (Gemini) -> voice (edge-tts) -> render (Remotion) -> upload (YouTube)."""
import asyncio
import datetime
import json
import math
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
CFG = json.loads((ROOT / 'config.json').read_text(encoding='utf-8'))
HIST = ROOT / 'data' / 'history.json'
OUT = ROOT / 'out'
PUB = ROOT / 'public'
FPS = 30
ANIMS = ['pop', 'bounce', 'float', 'spin', 'shake', 'slide']
HEX = re.compile(r'^#[0-9a-fA-F]{6}$')

CATEGORIES = [
    'a tall tale about an absurdly gigantic animal',
    'a tall tale about a town where the weather behaves ridiculously',
    'a funny what-if about space (the moon, the sun, planets) told as a tall tale',
    'a tall tale about a legendary hero with one impossible talent (an original character)',
    'a tall tale that secretly teaches one TRUE, surprising science fact',
    'a tall tale about runaway food (giant pizza, escaping pancake, a soup the size of a lake)',
    'a tall tale about a super-strong kid and their unusual pet',
    'a tall tale about a river or the ocean and a ridiculous sea creature',
    'a tall tale about a tiny creature that did something enormous',
    'a tall tale about the fastest, loudest or tallest thing in the world',
]


def clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, float(v)))
    except (TypeError, ValueError):
        return default


def gemini(prompt, retries=4):
    key = os.environ['GEMINI_API_KEY']
    model = os.environ.get('GEMINI_MODEL') or CFG['gemini_model']
    url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
    body = json.dumps({
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'temperature': 1.0, 'responseMimeType': 'application/json'},
    }).encode()
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(
                url, data=body, headers={'Content-Type': 'application/json', 'x-goog-api-key': key}
            )
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.load(r)
            return json.loads(data['candidates'][0]['content']['parts'][0]['text'])
        except Exception as e:  # noqa: BLE001
            last = e
            print(f'gemini retry {i + 1}: {e}', file=sys.stderr)
            time.sleep(5 * (i + 1))
    raise RuntimeError(f'Gemini failed: {last}')


def clean_scene(s):
    emos = []
    for e in (s.get('emojis') or [])[:4]:
        ch = str(e.get('char', '')).strip()
        if not ch:
            continue
        anim = e.get('anim')
        emos.append({
            'char': ch,
            'x': clamp(e.get('x'), 10, 90, 50),
            'y': clamp(e.get('y'), 15, 66, 40),
            'size': clamp(e.get('size'), 100, 340, 220),
            'anim': anim if anim in ANIMS else 'pop',
        })
    if not emos:
        emos = [{'char': '⭐', 'x': 50, 'y': 40, 'size': 240, 'anim': 'bounce'}]
    bg = list(s.get('bg') or []) + [None, None]
    bg = [c if (isinstance(c, str) and HEX.match(c)) else d for c, d in zip(bg[:2], ['#ffb347', '#ff6f91'])]
    narration = str(s.get('narration', '')).strip()
    caption = str(s.get('caption', '')).strip() or narration[:40]
    if not narration:
        raise ValueError('scene without narration')
    return {'narration': narration, 'caption': caption, 'emojis': emos, 'bg': bg}


MASTER_PROMPT = """You write scripts for a 30-second vertical cartoon YouTube Short.
Style: a TALL TALE - wildly exaggerated, funny, warm, family-friendly, told like a campfire storyteller.
Today's category: {cat}.
Do NOT reuse or closely resemble these recent topics: {recent}.
Rules:
- Exactly 6 scenes. Each narration is 11-14 words (about 75 words total, ~30 seconds spoken).
- Scene 1 must hook the viewer within 3 seconds. The last scene lands a punchline or a twist.
- caption = punchy on-screen text, 3-7 words.
- Each scene has 2-4 emojis that illustrate it (single emoji characters only, no text).
  x in 15-85, y in 18-62 (percent of screen), size 120-320, anim one of {anims}.
- bg = two bright cartoon hex colors like "#ffb347", different for every scene.
- No violence, no real people, no brands, no politics.
Return ONLY JSON:
{{"topic": "short topic name",
 "title": "catchy title under 70 characters",
 "description": "2 sentences for the video description",
 "tags": ["8 to 12 short tags"],
 "scenes": [{{"narration": "...", "caption": "...", "emojis": [{{"char": "🐓", "x": 50, "y": 40, "size": 240, "anim": "bounce"}}], "bg": ["#ffb347", "#ff6f91"]}}]}}"""

LOCAL_PROMPT = """Translate and naturally localize this short cartoon story into {lang} (language code {code}).
Keep the humor, keep each narration about the same length so it takes ~30 seconds to speak.
Write like a native storyteller, not a literal translation. Do not use emojis in the text.
Source JSON:
{src}
Return ONLY JSON:
{{"title": "...", "description": "...", "tags": ["..."], "scenes": [{{"narration": "...", "caption": "..."}}]}}
The scenes array must have exactly {n} items, in the same order."""


def make_master(recent, today):
    cat = CATEGORIES[today.toordinal() % len(CATEGORIES)]
    prompt = MASTER_PROMPT.format(cat=cat, recent='; '.join(recent[-60:]) or 'none', anims=ANIMS)
    for _ in range(3):
        m = gemini(prompt)
        try:
            scenes = [clean_scene(s) for s in m['scenes']]
            if 4 <= len(scenes) <= 8:
                return {
                    'topic': str(m.get('topic') or m['title']),
                    'title': str(m['title']),
                    'description': str(m.get('description', '')),
                    'tags': [str(t) for t in m.get('tags', [])],
                    'scenes': scenes,
                }
        except (KeyError, TypeError, ValueError) as e:
            print('bad master, retrying:', e, file=sys.stderr)
    raise RuntimeError('could not get a valid story')


def localize(master, lang):
    src = json.dumps({
        'title': master['title'],
        'description': master['description'],
        'tags': master['tags'],
        'scenes': [{'narration': s['narration'], 'caption': s['caption']} for s in master['scenes']],
    }, ensure_ascii=False)
    prompt = LOCAL_PROMPT.format(lang=lang['name'], code=lang['code'], src=src, n=len(master['scenes']))
    for _ in range(3):
        m = gemini(prompt)
        try:
            if len(m['scenes']) == len(master['scenes']):
                return {
                    'title': str(m['title']),
                    'description': str(m.get('description', '')),
                    'tags': [str(t) for t in m.get('tags', [])],
                    'texts': [(str(s['narration']).strip(), str(s['caption']).strip()) for s in m['scenes']],
                }
        except (KeyError, TypeError) as e:
            print('bad localization, retrying:', e, file=sys.stderr)
    raise RuntimeError(f"could not localize to {lang['code']}")


async def _edge(text, voice, path):
    import edge_tts

    await edge_tts.Communicate(text, voice, rate='+4%').save(str(path))


def tts(text, lang, voice, path):
    try:
        asyncio.run(_edge(text, voice, path))
        if path.stat().st_size < 1000:
            raise RuntimeError('empty audio')
    except Exception as e:  # noqa: BLE001
        print(f'edge-tts failed ({e}); falling back to gTTS', file=sys.stderr)
        from gtts import gTTS

        gTTS(text, lang=lang).save(str(path))


def duration(path):
    out = subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(path)], text=True
    )
    return float(out.strip())


def build_props(master, loc, lang):
    scenes = []
    for i, s in enumerate(master['scenes']):
        narration, caption = loc['texts'][i] if loc else (s['narration'], s['caption'])
        rel = f"audio/{lang['code']}_{i}.mp3"
        tts(narration, lang['code'], lang['voice'], PUB / rel)
        frames = max(45, math.ceil((duration(PUB / rel) + 0.5) * FPS))
        scenes.append({'caption': caption, 'emojis': s['emojis'], 'bg': s['bg'], 'audio': rel, 'frames': frames})
    total = sum(s['frames'] for s in scenes) + 15
    return {'durationInFrames': total, 'music': 'music.wav', 'scenes': scenes}


def render(props, code):
    props_path = OUT / f'props_{code}.json'
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding='utf-8')
    video = OUT / f'{code}.mp4'
    subprocess.run(
        ['npx', 'remotion', 'render', 'src/index.ts', 'Story', str(video),
         f'--props={props_path}', '--codec=h264', '--crf=24', '--log=warn'],
        cwd=ROOT, check=True,
    )
    return video


def main():
    OUT.mkdir(exist_ok=True)
    (PUB / 'audio').mkdir(parents=True, exist_ok=True)
    today = datetime.date.today()
    hist = json.loads(HIST.read_text(encoding='utf-8')) if HIST.exists() else {'topics': []}

    langs = CFG['languages']
    only = [x.strip() for x in os.environ.get('LANGS', '').split(',') if x.strip()]
    if only:
        langs = [lg for lg in langs if lg['code'] in only]

    creds_ok = all(os.environ.get(k) for k in ('YT_CLIENT_ID', 'YT_CLIENT_SECRET', 'YT_REFRESH_TOKEN'))
    want_upload = os.environ.get('UPLOAD', 'false').lower() == 'true'
    if want_upload and not creds_ok:
        print('YouTube secrets missing: videos will be rendered but not uploaded.')
    do_upload = want_upload and creds_ok
    if do_upload:
        from upload_youtube import upload

    master = make_master([t['topic'] for t in hist['topics']], today)
    print('Topic:', master['topic'])
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'make_music.py'), str(PUB / 'music.wav'),
                    str(today.toordinal())], check=True)

    done, uploads = [], 0
    for lang in langs:
        code = lang['code']
        try:
            loc = None if code == 'en' else localize(master, lang)
            props = build_props(master, loc, lang)
            video = render(props, code)
            print(f"[{code}] rendered {video.name}, {props['durationInFrames'] / FPS:.1f}s")
            done.append(code)
            if do_upload and uploads < CFG.get('max_uploads_per_day', 6):
                title = (loc['title'] if loc else master['title']).strip()
                if '#shorts' not in title.lower():
                    title = f'{title[:88]} #Shorts'
                desc = (loc['description'] if loc else master['description']).strip()
                desc += '\n\n#Shorts #cartoon #story\nMade with AI-assisted tools.'
                tags = (loc['tags'] if loc else master['tags']) + ['Shorts']
                vid = upload(str(video), title, desc, tags, code, CFG.get('privacy', 'public'))
                uploads += 1
                print(f'[{code}] uploaded https://youtu.be/{vid}')
        except Exception as e:  # noqa: BLE001
            print(f'[{code}] FAILED: {e}', file=sys.stderr)

    hist['topics'].append({'date': today.isoformat(), 'topic': master['topic'], 'title': master['title']})
    hist['topics'] = hist['topics'][-400:]
    HIST.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding='utf-8')
    if not done:
        sys.exit(1)


if __name__ == '__main__':
    main()
