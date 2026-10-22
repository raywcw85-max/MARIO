"""將 AI 產生的豬仔姿勢圖（assets/entities/source/*.jpg）轉換成
遊戲需要的 spritesheet（含透明背景）。

用法：
    python3 tools/generate_pig_sprites.py
需求：Pillow（pip install pillow）

輸出（6 倍解析度，透明背景）：
    assets/entities/mario.png        (6 frames, 648x96 -> 每格 108x96)
    assets/entities/mario-grown.png  (6 frames, 648x192 -> 每格 108x192)
    assets/entities/mario-fire.png   (7 frames, 756x192 -> 每格 108x192)

注意：直接把 AI 原圖（4128x1024 / 5376x796 的 JPEG）改名成 .png 放到
assets/entities/ 是無法使用的，遊戲會用 18x16 / 18x32 去切圖。請把原圖放在
assets/entities/source/ 再執行此工具。
"""
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parent.parent

SRC = {
    'small': {
        'path': ROOT / 'assets/entities/source/pig-small.jpg',
        'out': ROOT / 'assets/entities/mario.png',
        'poses': [(190, 712), (1118, 1668), (1766, 2566), (2739, 3529), (3576, 4415), (4688, 5337)],
        'frames': 6,  # idle / run x3 / hurt / jump
        'frame': (18, 16),
    },
    'grown': {
        'path': ROOT / 'assets/entities/source/pig-grown.jpg',
        'out': ROOT / 'assets/entities/mario-grown.png',
        'poses': [(24, 644), (789, 1411), (1493, 2024), (2099, 2726), (2815, 3370), (3466, 4127)],
        'frames': 6,  # idle / run x3 / crouch / jump
        'frame': (18, 32),
    },
    'fire': {
        'path': ROOT / 'assets/entities/source/pig-fire.jpg',
        'out': ROOT / 'assets/entities/mario-fire.png',
        'poses': [(55, 597), (728, 1316), (1323, 1815), (1864, 2378), (2414, 2917), (3521, 4068), (2968, 3497)],
        'frames': 7,  # idle / run x3 / crouch / jump / throw(arm up)
        'frame': (18, 32),
        'whiten': True,  # AI 圖把棋盤格背景烘焙進白色衣服內，需要美白處理
    },
}

DS = 4  # 背景 flood fill 前先縮小的倍率
SCALE = 6  # 輸出解析度倍率：18x16 -> 108x96、18x32 -> 108x192（需與 game.js 的 playerSpriteScale 一致）


def is_bg(px):
    r, g, b = px
    return min(r, g, b) >= 190 and max(r, g, b) - min(r, g, b) <= 22


def background_mask(im):
    """從圖片邊界 flood fill，找出與邊界相連的淺色棋盤格背景。"""
    w, h = im.size
    small = im.resize((w // DS, h // DS), Image.BOX)
    sw, sh = small.size
    pix = small.load()
    bg = bytearray(sw * sh)
    q = deque()
    for x in range(sw):
        for y in (0, sh - 1):
            if not bg[y * sw + x] and is_bg(pix[x, y]):
                bg[y * sw + x] = 1
                q.append((x, y))
    for y in range(sh):
        for x in (0, sw - 1):
            if not bg[y * sw + x] and is_bg(pix[x, y]):
                bg[y * sw + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < sw and 0 <= ny < sh and not bg[ny * sw + nx] and is_bg(pix[nx, ny]):
                bg[ny * sw + nx] = 1
                q.append((nx, ny))
    mask = Image.new('L', (sw, sh))
    mask.putdata([255 if v else 0 for v in bg])
    return mask.resize((w, h), Image.NEAREST)


def downscale_rgba(im, alpha, size):
    """縮小 RGBA 圖，先與白色合成再還原 alpha，避免透明邊緣變黑。"""
    white = Image.new('RGB', im.size, (255, 255, 255))
    flat = Image.composite(im, white, alpha).resize(size, Image.LANCZOS)
    a = alpha.resize(size, Image.LANCZOS)
    out = flat.convert('RGBA')
    px = out.load()
    ap = a.load()
    for y in range(size[1]):
        for x in range(size[0]):
            r, g, b, _ = px[x, y]
            al = ap[x, y]
            if al == 0:
                px[x, y] = (0, 0, 0, 0)
            elif al < 255:
                f = al / 255.0
                px[x, y] = (max(0, min(255, round((r - 255 * (1 - f)) / f))),
                            max(0, min(255, round((g - 255 * (1 - f)) / f))),
                            max(0, min(255, round((b - 255 * (1 - f)) / f))), al)
    return out


def build(name, cfg):
    if not cfg['path'].exists():
        raise SystemExit('缺少原圖：%s（請把 AI 原圖放到這個位置）' % cfg['path'].relative_to(ROOT))

    frame_w, frame_h = cfg.get('frame', (18, 32))
    frame_w *= SCALE
    frame_h *= SCALE
    im = Image.open(cfg['path']).convert('RGB')
    w, h = im.size

    bgmask = background_mask(im)
    alpha = bgmask.point(lambda v: 0 if v else 255)
    # 侵蝕輪廓，去掉棋盤格的抗鋸齒殘影
    alpha = alpha.filter(ImageFilter.MinFilter(9))

    if cfg.get('whiten'):
        r, g, b = im.split()
        maxc = ImageChops.lighter(ImageChops.lighter(r, g), b)
        minc = ImageChops.darker(ImageChops.darker(r, g), b)
        light = minc.point(lambda v: 255 if v >= 170 else 0)
        low_sat = ImageChops.subtract(maxc, minc).point(lambda v: 255 if v <= 25 else 0)
        inside = ImageChops.multiply(ImageChops.multiply(light, low_sat),
                                     alpha.point(lambda v: 255 if v > 0 else 0))
        im = Image.composite(Image.new('RGB', im.size, (255, 255, 255)), im, inside)

    boxes = []
    for (x0, x1) in cfg['poses']:
        bb = alpha.crop((x0, 0, x1 + 1, h)).getbbox()
        if not bb:
            raise SystemExit('找不到姿勢: %s %s' % (name, (x0, x1)))
        boxes.append((x0 + bb[0], bb[1], x0 + bb[2], bb[3]))

    widths = [b[2] - b[0] for b in boxes]
    heights = [b[3] - b[1] for b in boxes]
    scale = min(frame_w / max(widths), frame_h / max(heights))

    sheet = Image.new('RGBA', (frame_w * cfg['frames'], frame_h), (0, 0, 0, 0))
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        pose = im.crop((x0, y0, x1, y1))
        pa = alpha.crop((x0, y0, x1, y1))
        nw = max(1, round((x1 - x0) * scale))
        nh = max(1, round((y1 - y0) * scale))
        small = downscale_rgba(pose, pa, (nw, nh))
        sheet.alpha_composite(small, (i * frame_w + (frame_w - nw) // 2, frame_h - nh))

    sheet.save(cfg['out'])
    print('已輸出 %s %s' % (cfg['out'].relative_to(ROOT), sheet.size))


if __name__ == '__main__':
    for name, cfg in SRC.items():
        build(name, cfg)
