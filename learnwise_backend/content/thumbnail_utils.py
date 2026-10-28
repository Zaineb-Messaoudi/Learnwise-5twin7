"""
Thumbnail generation utilities using Pillow.

Generates preview thumbnails for course materials:
- Images: resized to thumbnail size
- PDF: first page rendered (requires PyMuPDF/fitz) or type placeholder
- Video: frame extraction (requires cv2) or type placeholder
- Audio: waveform visualization
- Code: syntax-themed placeholder
- Other: generic type placeholder
"""

import io
import os
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile


THUMBNAIL_SIZE = (300, 300)

# Type colors for placeholders
TYPE_COLORS = {
    'document': '#4A90E2',   # blue
    'audio': '#E67E22',      # orange
    'video': '#E74C3C',      # red
    'code': '#2ECC71',       # green
    'markdown': '#9B59B6',   # purple
    'latex': '#34495E',      # dark blue-gray
    'other': '#7F8C8D',      # gray
}

TYPE_LABELS = {
    'document': 'DOC',
    'audio': 'AUDIO',
    'video': 'VIDEO',
    'code': 'CODE',
    'markdown': 'MD',
    'latex': 'LaTeX',
    'other': 'FILE',
}


def _get_font(size=40):
    """Try to load a DejaVu font, fall back to default."""
    for path in [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/calibrib.ttf',
    ]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_placeholder(material_type, output_size=THUMBNAIL_SIZE):
    """Generate a colored placeholder with type label."""
    color = TYPE_COLORS.get(material_type, TYPE_COLORS['other'])
    label = TYPE_LABELS.get(material_type, TYPE_LABELS['other'])

    img = Image.new('RGB', output_size, color)
    draw = ImageDraw.Draw(img)

    font = _get_font(size=60)
    text_bbox = draw.textbbox((0, 0), label, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    x = (output_size[0] - text_w) // 2
    y = (output_size[1] - text_h) // 2
    draw.text((x, y), label, fill='white', font=font)

    return img


def generate_thumbnail(material):
    """
    Generate a thumbnail for a CourseMaterial instance.

    Saves the thumbnail to material.thumbnail and returns the material.
    Does NOT save the material instance (caller must call material.save()).
    """
    if not material.file:
        return material

    file_path = material.file.path
    material_type = material.material_type

    try:
        if material_type == 'document' and file_path.lower().endswith('.pdf'):
            img = _pdf_first_page(file_path)
        elif material_type == 'video':
            img = _video_frame(file_path)
        elif material_type == 'audio':
            img = _audio_waveform(material_type)
        elif material_type == 'code':
            img = _code_placeholder(material_type)
        elif material_type in ('document', 'markdown', 'latex'):
            img = _document_placeholder(material_type)
        else:
            # Try to open as image
            try:
                img = Image.open(file_path)
                img = img.convert('RGB')
                img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
                # Pad to square
                square = Image.new('RGB', THUMBNAIL_SIZE, '#2C3E50')
                square.paste(img, ((THUMBNAIL_SIZE[0] - img.size[0]) // 2,
                                   (THUMBNAIL_SIZE[1] - img.size[1]) // 2))
                img = square
            except Exception:
                img = _draw_placeholder(material_type)
    except Exception:
        img = _draw_placeholder(material_type)

    # Save to BytesIO
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    # Generate filename
    base_name = os.path.splitext(os.path.basename(material.file.name))[0]
    thumb_name = f"{base_name}_thumb.png"

    material.thumbnail.save(thumb_name, ContentFile(buf.read()), save=False)
    return material


def _pdf_first_page(file_path):
    """Render first page of PDF to image. Requires PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        doc.close()
        img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
        square = Image.new('RGB', THUMBNAIL_SIZE, TYPE_COLORS['document'])
        square.paste(img, ((THUMBNAIL_SIZE[0] - img.size[0]) // 2,
                           (THUMBNAIL_SIZE[1] - img.size[1]) // 2))
        return square
    except ImportError:
        return _draw_placeholder('document')


def _video_frame(file_path):
    """Extract a frame from video. Requires opencv-python (cv2)."""
    try:
        import cv2
        cap = cv2.VideoCapture(file_path)
        ret, frame = cap.read()
        cap.release()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img.thumbnail(THUMBNAIL_SIZE, Image.LANCZOS)
            square = Image.new('RGB', THUMBNAIL_SIZE, TYPE_COLORS['video'])
            square.paste(img, ((THUMBNAIL_SIZE[0] - img.size[0]) // 2,
                               (THUMBNAIL_SIZE[1] - img.size[1]) // 2))
            return square
    except ImportError:
        pass
    return _draw_placeholder('video')


def _audio_waveform(material_type):
    """Generate a simple waveform visualization."""
    img = Image.new('RGB', THUMBNAIL_SIZE, TYPE_COLORS.get(material_type, '#E67E22'))
    draw = ImageDraw.Draw(img)

    import random
    random.seed(42)
    center_y = THUMBNAIL_SIZE[1] // 2
    x = 20
    while x < THUMBNAIL_SIZE[0] - 20:
        height = random.randint(10, 80)
        y = center_y - height // 2
        draw.rectangle([x, y, x + 4, y + height], fill='white')
        x += 8

    font = _get_font(size=36)
    label = TYPE_LABELS.get(material_type, 'AUDIO')
    text_bbox = draw.textbbox((0, 0), label, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    draw.text(
        ((THUMBNAIL_SIZE[0] - text_w) // 2, THUMBNAIL_SIZE[1] - text_h - 20),
        label, fill='white', font=font,
    )
    return img


def _document_placeholder(material_type):
    """Placeholder for document/markdown/latex types."""
    return _draw_placeholder(material_type)


def _code_placeholder(material_type):
    """Placeholder for code type."""
    return _draw_placeholder(material_type)
