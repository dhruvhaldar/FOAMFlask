from PIL import Image, ImageDraw, ImageFont
import os

# Create output directory if it doesn't exist
os.makedirs('../static', exist_ok=True)

# Create a simple 32x32 black square with a white 'F' for FOAMFlask
img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rectangle([5, 5, 27, 27], fill='#1E88E5')  # Material Blue 600

# Create font object with size
try:
    font = ImageFont.truetype("arial.ttf", 24)
except IOError:
    font = ImageFont.load_default()

d.text((10, 5), 'F', fill='white', font=font)

# Save as favicon.ico in the static directory - using raw string
img.save(r'E:\Misc\FOAMFlask\static\favicon.ico', format='ICO', sizes=[(32, 32)])

# Or alternatively, you can use forward slashes which work on Windows too:
# img.save('E:/Misc/FOAMFlask/static/favicon.ico', format='ICO', sizes=[(32, 32)])

print("Favicon created successfully!")