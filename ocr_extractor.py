import os
import io

# Minimum average characters per page to consider a PDF text-based
SPARSE_THRESHOLD = 50


def is_sparse(text, page_count):
    """Return True if the PDF likely needs OCR."""
    if page_count == 0:
        return True
    avg = len(text.strip()) / page_count
    return avg < SPARSE_THRESHOLD


def ocr_pdf(filepath, on_progress=None):
    """OCR a PDF file page by page. Returns extracted text string."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "pytesseract or Pillow not installed.\n"
            "Run: sudo apt install tesseract-ocr python3-pil\n"
            "Then: pip3 install --user pytesseract"
        )

    try:
        import gi
        gi.require_version('Poppler', '0.18')
        from gi.repository import Poppler
    except Exception:
        raise RuntimeError("Poppler not installed.\nRun: sudo apt install gir1.2-poppler-0.18")

    import cairo

    uri = 'file://' + os.path.abspath(filepath)
    doc = Poppler.Document.new_from_file(uri)
    page_count = doc.get_n_pages()
    pages_text = []

    for i in range(page_count):
        if on_progress:
            on_progress(i + 1, page_count)

        page = doc.get_page(i)
        pw, ph = page.get_size()
        # Render at 2x scale for better OCR accuracy
        scale = 2.0
        w, h = int(pw * scale), int(ph * scale)

        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
        ctx = cairo.Context(surface)
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        ctx.scale(scale, scale)
        page.render(ctx)
        surface.flush()

        # Convert Cairo surface to PIL Image via PNG
        buf = io.BytesIO()
        surface.write_to_png(buf)
        buf.seek(0)
        img = Image.open(buf)

        text = pytesseract.image_to_string(img)
        if text.strip():
            pages_text.append(text.strip())

    return '\n\n'.join(pages_text), page_count
