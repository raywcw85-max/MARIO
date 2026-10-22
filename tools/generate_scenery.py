"""將 AI 產生的場景圖（assets/scenery/source/*.jpg）轉換成遊戲用 PNG。

用法：
    python3 tools/generate_scenery.py
需求：Pillow（pip install pillow）

原始圖其實都是 JPEG（即使副檔名被改成 .png），而且解析度遠大於遊戲需求，
直接放進 assets/scenery/ 會讓城堡連隔壁棟、模糊照片、路燈吊牌一起畫出來。
此工具會：

    castle.jpg -> assets/scenery/castle.png
        裁出「Naughty Nuri's」主棟（左邊的福隆騎樓、右邊模糊照片與路燈都不留），
        蓋掉掛在右牆上的路燈鐵件與吊牌，再縮到 640px 高（708x640）。
        來源圖最上層的拱窗被圖片邊界切掉，因此從上層陽台下緣開始裁，
        讓 sprite 頂部是乾淨的水平線。

    sign.jpg   -> assets/scenery/sign.png
        保留 1024x512 原生解析度，只轉成 PNG（不重新取樣）。

顯示大小由 javascript/game.js 的 castleScale / signScale 控制，需與此處一致：
    castle.png 高度 640 -> castleScale = screenHeight / 2400
    sign.png   高度 512 -> signScale   = screenHeight / 2036
"""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent

CASTLE_SRC = ROOT / 'assets/scenery/source/castle.jpg'
CASTLE_OUT = ROOT / 'assets/scenery/castle.png'

# 主棟建築的範圍（原始 2400x1792 圖片座標）：
# x 515 是左側黑邊，x 1922 是右側黑邊，y 1651 切在騎樓地坪線。
# y 380 是上層陽台下緣：來源圖最上層窗戶被裁掉，從這裡切才不會留下半個拱窗。
CASTLE_CROP = (515, 380, 1922, 1651)

# 右牆上的路燈鐵件與吊牌，原圖座標 (x0, y0, x1, y1)。
# 用同高度乾淨牆面的顏色（取樣自 y=1000 那一列）覆蓋，包含右側黑邊。
CASTLE_CLEAN_RECTS = (
    (1858, 820, 1922, 975),
    (1855, 1035, 1922, 1255),
)
CASTLE_CLEAN_SAMPLE_Y = 1000

# 輸出高度：1080p 下城堡約顯示 317px 高，640px 來源約為 2 倍像素密度；
# 4K（顯示約 634px）時也幾乎是 1:1，不需要更大的圖。
CASTLE_HEIGHT = 640

SIGN_SRC = ROOT / 'assets/scenery/source/sign.jpg'
SIGN_OUT = ROOT / 'assets/scenery/sign.png'


def clean_castle(crop):
    """把路燈與吊牌覆蓋成乾淨的牆面（保留最右側黑色輪廓）。"""
    left, top, _, _ = CASTLE_CROP
    sample_y = CASTLE_CLEAN_SAMPLE_Y - top

    for x0, y0, x1, y1 in CASTLE_CLEAN_RECTS:
        for x in range(x0 - left, x1 - left):
            color = crop.getpixel((x, sample_y))
            for y in range(y0 - top, y1 - top):
                crop.putpixel((x, y), color)


def build_castle():
    image = Image.open(CASTLE_SRC).convert('RGB').crop(CASTLE_CROP)
    clean_castle(image)

    width = round(image.width * CASTLE_HEIGHT / image.height)
    image = image.resize((width, CASTLE_HEIGHT), Image.LANCZOS).convert('RGBA')
    image.save(CASTLE_OUT, optimize=True)
    print(f'{CASTLE_OUT.relative_to(ROOT)}: {image.width}x{image.height}')


def build_sign():
    image = Image.open(SIGN_SRC).convert('RGBA')
    image.save(SIGN_OUT, optimize=True)
    print(f'{SIGN_OUT.relative_to(ROOT)}: {image.width}x{image.height}')


if __name__ == '__main__':
    build_castle()
    build_sign()
