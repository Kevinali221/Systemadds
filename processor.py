import logging
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

import config

log = logging.getLogger(__name__)

FALLBACK_FONTS = [
    "DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
]


class AdBannerError(Exception):
    pass


def _rgba(hex_color, alpha=255):
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


class AdBannerGenerator:
    def __init__(self, format_key="story", font_path=None):
        if format_key not in config.FORMATS:
            raise ValueError(f"Formato inválido '{format_key}'. Usa: {list(config.FORMATS)}")
        self.format_key = format_key
        self.size = config.FORMATS[format_key]
        self.width, self.height = self.size
        self.scale = self.width / 1080
        self.font_path = self._resolve_font(font_path)
        self.canvas = None

    # ---------- utilidades ----------
    def _resolve_font(self, font_path):
        candidates = [Path(font_path)] if font_path else []
        candidates += sorted(config.ASSETS_DIR.glob("*.ttf"))
        for c in candidates:
            try:
                ImageFont.truetype(str(c), 10)
                return str(c)
            except OSError:
                log.warning("No se pudo cargar la fuente %s", c)
        for name in FALLBACK_FONTS:
            try:
                ImageFont.truetype(name, 10)
                return name
            except OSError:
                continue
        log.warning("Usando fuente por defecto de PIL")
        return None

    def font(self, size):
        size = max(8, int(size * self.scale))
        if self.font_path:
            try:
                return ImageFont.truetype(self.font_path, size)
            except OSError:
                pass
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()

    def _fit_font(self, draw, text, size, max_width):
        f = self.font(size)
        while draw.textlength(text, font=f) > max_width and size > 10:
            size -= 2
            f = self.font(size)
        return f

    def _wrap(self, draw, text, font, max_width):
        lines, line = [], ""
        for word in text.split():
            test = f"{line} {word}".strip()
            if draw.textlength(test, font=font) <= max_width or not line:
                line = test
            else:
                lines.append(line)
                line = word
        if line:
            lines.append(line)
        return lines

    def _overlay(self, painter):
        layer = Image.new("RGBA", self.size, (0, 0, 0, 0))
        painter(ImageDraw.Draw(layer), layer)
        self.canvas = Image.alpha_composite(self.canvas, layer)

    # ---------- 1. redimensionamiento ----------
    def load_and_fit(self, photo_path):
        photo_path = Path(photo_path)
        if not photo_path.is_file():
            raise AdBannerError(f"Foto no encontrada: {photo_path}")
        try:
            with Image.open(photo_path) as im:
                im = ImageOps.exif_transpose(im).convert("RGB")
        except (UnidentifiedImageError, OSError, SyntaxError) as e:
            raise AdBannerError(f"Foto dañada o ilegible ({photo_path.name}): {e}") from e
        fitted = ImageOps.fit(im, self.size, Image.LANCZOS, centering=(0.5, 0.5))
        self.canvas = fitted.convert("RGBA")
        return self.canvas

    # ---------- 2. capas ----------
    def add_top_bar(self, logo_path=None):
        s = self.scale
        bar_h = int(170 * s)
        pad = int(36 * s)
        navy = config.COLORS["navy"]

        def paint(d, layer):
            d.rectangle([0, 0, self.width, bar_h], fill=_rgba(navy, 215))
            d.rectangle([0, bar_h - int(5 * s), self.width, bar_h], fill=_rgba(config.COLORS["primary"]))
        self._overlay(paint)

        self._paste_logo(logo_path or config.LOGO_PATH, pad, bar_h, int(bar_h * 0.72))

        d = ImageDraw.Draw(self.canvas)
        bw, bh, gap = int(215 * s), int(78 * s), int(18 * s)
        y = (bar_h - bh) // 2
        x2 = self.width - pad - bw
        x1 = x2 - gap - bw
        self._button(d, (x1, y, x1 + bw, y + bh), "CALL NOW",
                     config.COLORS["primary"], config.COLORS["white"], 30)
        self._button(d, (x2, y, x2 + bw, y + bh), "WhatsApp",
                     "#25D366", config.COLORS["white"], 30)
        self.bar_h = bar_h

    def _paste_logo(self, logo_path, x, bar_h, max_h):
        try:
            with Image.open(logo_path) as lg:
                lg = lg.convert("RGBA")
        except (FileNotFoundError, UnidentifiedImageError, OSError) as e:
            log.warning("Logo no disponible (%s); se usa el nombre como texto.", e)
            d = ImageDraw.Draw(self.canvas)
            f = self._fit_font(d, config.BUSINESS_NAME, 40, int(self.width * 0.32))
            h = d.textbbox((0, 0), config.BUSINESS_NAME, font=f)[3]
            d.text((x, (bar_h - h) // 2), config.BUSINESS_NAME, font=f, fill=config.COLORS["white"])
            return
        ratio = max_h / lg.height
        lg = lg.resize((max(1, int(lg.width * ratio)), max_h), Image.LANCZOS)
        self.canvas.alpha_composite(lg, (x, (bar_h - max_h) // 2))

    def _button(self, d, box, text, fill, text_fill, size):
        radius = (box[3] - box[1]) // 2
        d.rounded_rectangle(box, radius=radius, fill=fill)
        f = self._fit_font(d, text, size, (box[2] - box[0]) - int(24 * self.scale))
        d.text(((box[0] + box[2]) / 2, (box[1] + box[3]) / 2), text,
               font=f, fill=text_fill, anchor="mm")

    def add_bottom_gradient(self, height_ratio=0.55, max_alpha=240):
        h = int(self.height * height_ratio)
        grad = Image.new("L", (1, h))
        for y in range(h):
            t = y / (h - 1)
            grad.putpixel((0, y), int(max_alpha * (t ** 1.6)))
        grad = grad.resize((self.width, h))
        black = Image.new("RGBA", (self.width, h), _rgba(config.COLORS["dark"]))
        black.putalpha(grad)
        layer = Image.new("RGBA", self.size, (0, 0, 0, 0))
        layer.paste(black, (0, self.height - h))
        self.canvas = Image.alpha_composite(self.canvas, layer)

    # ---------- 3. textos ----------
    def add_texts(self, headline, subtitle, service, footer_reserved=None):
        """Bloque de texto sobre el pie: servicio, titular (ES) y subtítulo (EN)."""
        s = self.scale
        d = ImageDraw.Draw(self.canvas)
        margin = int(60 * s)
        max_w = self.width - 2 * margin
        footer_top = self.height - (footer_reserved or int(330 * s))

        head_f = self.font(86)
        head_lines = self._wrap(d, headline.upper(), head_f, max_w)
        while len(head_lines) > 3 and head_f.size > 30:
            head_f = self.font(head_f.size / s - 6)
            head_lines = self._wrap(d, headline.upper(), head_f, max_w)
        sub_f = self.font(40)
        sub_lines = self._wrap(d, subtitle, sub_f, max_w)
        tag_f = self.font(34)

        lh_head, lh_sub, tag_h = int(head_f.size * 1.15), int(sub_f.size * 1.35), int(34 * s * 2.0)
        total = tag_h + int(20 * s) + lh_head * len(head_lines) + int(16 * s) + lh_sub * len(sub_lines)
        y = footer_top - total

        tag = service.upper()
        tw = int(d.textlength(tag, font=tag_f)) + int(44 * s)
        d.rounded_rectangle((margin, y, margin + tw, y + tag_h), radius=tag_h // 2,
                            fill=config.COLORS["primary"])
        d.text((margin + tw / 2, y + tag_h / 2), tag, font=tag_f,
               fill=config.COLORS["white"], anchor="mm")
        y += tag_h + int(20 * s)
        for ln in head_lines:
            d.text((margin, y), ln, font=head_f, fill=config.COLORS["white"],
                   stroke_width=max(1, int(2 * s)), stroke_fill=config.COLORS["dark"])
            y += lh_head
        y += int(16 * s)
        for ln in sub_lines:
            d.text((margin, y), ln, font=sub_f, fill="#D6E4FF")
            y += lh_sub

    def add_footer(self, cta_text="¡Escríbenos para agendar tu cita hoy!"):
        s = self.scale
        d = ImageDraw.Draw(self.canvas)
        margin = int(60 * s)
        max_w = self.width - 2 * margin

        bh = int(96 * s)
        by = self.height - int(250 * s)
        self._button(d, (margin, by, self.width - margin, by + bh), cta_text,
                     config.COLORS["primary"], config.COLORS["white"], 40)

        y = by + bh + int(24 * s)
        f = self._fit_font(d, config.ADDRESS, 30, max_w)
        d.text((self.width / 2, y), config.ADDRESS, font=f,
               fill=config.COLORS["white"], anchor="ma")
        phones = "  |  ".join(config.PHONES)
        f2 = self._fit_font(d, phones, 28, max_w)
        d.text((self.width / 2, y + int(44 * s)), phones, font=f2,
               fill="#D6E4FF", anchor="ma")

    # ---------- 4. salida ----------
    def save(self, out_path):
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.canvas.convert("RGB").save(out_path, "JPEG", quality=95,
                                            subsampling=0, optimize=True)
        except OSError as e:
            raise AdBannerError(f"No se pudo guardar {out_path}: {e}") from e
        return out_path

    def generate(self, photo_path, headline, subtitle, service,
                 output_name=None, logo_path=None, cta_text=None):
        photo_path = Path(photo_path)
        self.load_and_fit(photo_path)
        self.add_bottom_gradient()
        self.add_top_bar(logo_path)
        self.add_texts(headline, subtitle, service)
        if cta_text:
            self.add_footer(cta_text)
        else:
            self.add_footer()
        name = output_name or f"{photo_path.stem}_{self.format_key}.jpg"
        return self.save(config.OUTPUT_DIR / name)
