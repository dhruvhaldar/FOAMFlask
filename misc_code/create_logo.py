import os

# Configuration
COLOR_START = "#06b6d4"
COLOR_END = "#0e7490"
OVERLAY_OPACITY = 0.1  # Bit darker overlay
SHADOW_OPACITY = 0.3
SHADOW_BLUR = 2
TEXT_COLOR = "#111827"

LOGO_SVG_TEMPLATE = """<svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:{color_start};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{color_end};stop-opacity:1" />
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="{blur}" />
      <feOffset dx="1" dy="2" result="offsetblur" />
      <feComponentTransfer>
        <feFuncA type="linear" slope="{shadow_opacity}" />
      </feComponentTransfer>
      <feMerge>
        <feMergeNode />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
  <rect x="0" y="0" width="100" height="100" rx="20" ry="20" fill="url(#grad)" />
  <rect x="0" y="0" width="100" height="100" rx="20" ry="20" fill="black" fill-opacity="{overlay_opacity}" />
  <path d="M30 20 H75 V32 H45 V44 H65 V56 H45 V80 H30 Z" fill="white" filter="url(#shadow)" />
</svg>"""

BANNER_SVG_TEMPLATE = """<svg width="500" height="100" viewBox="0 0 500 100" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:{color_start};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{color_end};stop-opacity:1" />
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="{blur}" />
      <feOffset dx="1" dy="2" result="offsetblur" />
      <feComponentTransfer>
        <feFuncA type="linear" slope="{shadow_opacity}" />
      </feComponentTransfer>
      <feMerge>
        <feMergeNode />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
    <style>
      .text {{ font: bold 60px 'Inter', sans-serif; fill: {text_color}; }}
    </style>
  </defs>
  <!-- Logo -->
  <rect x="0" y="0" width="100" height="100" rx="20" ry="20" fill="url(#grad)" />
  <rect x="0" y="0" width="100" height="100" rx="20" ry="20" fill="black" fill-opacity="{overlay_opacity}" />
  <path d="M30 20 H75 V32 H45 V44 H65 V56 H45 V80 H30 Z" fill="white" filter="url(#shadow)" />
  <!-- Text -->
  <text x="120" y="70" class="text">FOAMFlask</text>
</svg>"""

def generate_svgs():
    logo_content = LOGO_SVG_TEMPLATE.format(
        color_start=COLOR_START,
        color_end=COLOR_END,
        overlay_opacity=OVERLAY_OPACITY,
        blur=SHADOW_BLUR,
        shadow_opacity=SHADOW_OPACITY
    )
    
    banner_content = BANNER_SVG_TEMPLATE.format(
        color_start=COLOR_START,
        color_end=COLOR_END,
        overlay_opacity=OVERLAY_OPACITY,
        blur=SHADOW_BLUR,
        shadow_opacity=SHADOW_OPACITY,
        text_color=TEXT_COLOR
    )
    
    os.makedirs('static/icons', exist_ok=True)
    
    with open('static/icons/logo.svg', 'w') as f:
        f.write(logo_content)
        print("Generated static/icons/logo.svg")
    
    with open('static/icons/banner.svg', 'w') as f:
        f.write(banner_content)
        print("Generated static/icons/banner.svg")

if __name__ == "__main__":
    generate_svgs()
