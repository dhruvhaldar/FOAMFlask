from PIL import Image, ImageDraw, ImageFont
import os

# Create a simple 32x32 gradient square with a white 'F' for FOAMFlask
width, height = 32, 32
img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Colors from original design
color_start = (30, 136, 229) # #1E88E5
color_end = (13, 71, 161)    # #0D47A1 (Subtle dark blue gradient)

# Draw vertical gradient
for y in range(height):
    r = int(color_start[0] + (color_end[0] - color_start[0]) * y / (height - 1))
    g = int(color_start[1] + (color_end[1] - color_start[1]) * y / (height - 1))
    b = int(color_start[2] + (color_end[2] - color_start[2]) * y / (height - 1))
    d.line([(0, y), (width, y)], fill=(r, g, b, 255))

# Create font object with size
try:
    # Try to find a nice font, otherwise fallback
    font_paths = ["arial.ttf", "DejaVuSans.ttf", "FreeSans.ttf"]
    font = None
    for path in font_paths:
        try:
            font = ImageFont.truetype(path, 22)
            break
        except IOError:
            continue
    if font is None:
        font = ImageFont.load_default()
except Exception:
    font = ImageFont.load_default()

# Centered 'F'
w_text = 12
h_text = 20
d.text(((width - w_text) // 2 - 1, (height - h_text) // 2 - 2), 'F', fill='white', font=font)

# Save as favicon.ico in the static directory
output_path = r'E:\Misc\FOAMFlask\static\favicon.ico'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
img.save(output_path, format='ICO', sizes=[(32, 32)])

print(f"Favicon created successfully at {output_path}!")