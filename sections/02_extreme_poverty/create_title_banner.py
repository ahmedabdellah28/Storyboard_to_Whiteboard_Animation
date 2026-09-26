import os
import sys
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"E:\image_to_animate"
SEC_DIR = os.path.join(ROOT_DIR, "sections", "02_extreme_poverty")
ASSETS_DIR = os.path.join(SEC_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# Generate Visual Whiteboard Title Banner for Section 02
text = "الطبقة الثانية: الفقر المدقع"
reshaped = arabic_reshaper.reshape(text)
bidi_t = get_display(reshaped)

w, h = 1000, 220
img = Image.new('RGBA', (w, h), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)

# Try fonts in order: arialbd, tahomabd, seguiemj
font_path = 'C:/Windows/Fonts/arialbd.ttf'
if not os.path.exists(font_path):
    font_path = 'C:/Windows/Fonts/tahomabd.ttf'

font = ImageFont.truetype(font_path, 60)
bbox = draw.textbbox((0, 0), bidi_t, font=font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
tx = (w - tw) // 2
ty = (h - th) // 2 - 14

draw.text((tx, ty), bidi_t, font=font, fill=(25, 25, 30, 255))
line_y = ty + th + 16
draw.line([(tx - 25, line_y), (tx + tw + 25, line_y)], fill=(35, 35, 40, 255), width=6)

banner_path = os.path.join(ASSETS_DIR, "r0_00_title_banner.png")
img.save(banner_path)
print(f"✓ Title banner saved to: {banner_path} ({w}x{h})")
