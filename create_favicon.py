"""
将图片转换为圆形 favicon
"""
from PIL import Image, ImageDraw
import os

input_path = r'D:\contest\UI\chat-app\public\avatars\image.png'
output_path = r'D:\contest\UI\chat-app\public\favicon.png'

# 打开图片
img = Image.open(input_path).convert("RGBA")

# 调整大小到 128x128（更高分辨率）
img = img.resize((128, 128), Image.Resampling.LANCZOS)

# 创建圆形 mask
mask = Image.new('L', (128, 128), 0)
draw = ImageDraw.Draw(mask)
draw.ellipse((0, 0, 127, 127), fill=255)

# 应用圆形 mask
result = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
result.paste(img, (0, 0), mask)

# 保存
result.save(output_path, 'PNG')
print(f"✅ 圆形 favicon 已生成: {output_path}")
