#!/usr/bin/env python3
"""
generate_figure2.py

Regenerates Figure 2 (Example of LLM in-text annotation and fuzzy string anchoring)
matching the exact original visual style and dimensions (1907 x 861), updated with:
- Canonical schema tag <CDRUG> (replacing legacy <DRUG>)
- Highlighted invalid/hallucinated tags (<DATE>) and altered text ('and')
- SequenceMatcher string-anchoring back to original narrative ("for unknown")
- High-resolution rendering and clear typography
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def draw_arrow(draw: ImageDraw.ImageDraw, x: int, y_start: int, y_end: int, width: int = 3, head_size: int = 15):
    # Shaft
    draw.line([(x, y_start), (x, y_end)], fill="black", width=width)
    # Head
    draw.line([(x - head_size, y_end - head_size), (x, y_end)], fill="black", width=width)
    draw.line([(x + head_size, y_end - head_size), (x, y_end)], fill="black", width=width)


def get_fonts():
    font_paths = [
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/ariali.ttf", "C:/Windows/Fonts/arialbi.ttf"),
        ("C:/Windows/Fonts/calibri.ttf", "C:/Windows/Fonts/calibrib.ttf", "C:/Windows/Fonts/calibrii.ttf", "C:/Windows/Fonts/calibriz.ttf"),
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/segoeuii.ttf", "C:/Windows/Fonts/segoeuiz.ttf"),
    ]
    for reg, bld, itl, bitl in font_paths:
        if Path(reg).exists() and Path(bld).exists() and Path(itl).exists():
            return {
                "regular": ImageFont.truetype(reg, 32),
                "bold": ImageFont.truetype(bld, 32),
                "italic": ImageFont.truetype(itl, 32),
                "badge": ImageFont.truetype(bld, 34),
            }
    default = ImageFont.load_default()
    return {"regular": default, "bold": default, "italic": default, "badge": default}


def draw_styled_segment(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font: ImageFont.ImageFont,
                        text_color: str = "black", bg_color: str | None = None, padding: int = 4) -> int:
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]

    if bg_color:
        draw.rectangle([x - padding, y - 2, x + w + padding, y + h + padding + 4], fill=bg_color)

    draw.text((x, y), text, fill=text_color, font=font)
    return w


def draw_badge(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font: ImageFont.ImageFont, color: str,
               pad_x: int = 20, pad_y: int = 10, stroke: int = 3):
    bbox = font.getbbox(text)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    
    rect_x0 = x
    rect_y0 = y
    rect_x1 = x + w + 2 * pad_x
    rect_y1 = y + h + 2 * pad_y
    
    draw.rectangle([rect_x0, rect_y0, rect_x1, rect_y1], outline=color, width=stroke)
    draw.text((x + pad_x, y + pad_y - 2), text, fill=color, font=font)
    return (rect_x0, rect_y0, rect_x1, rect_y1)


def main():
    repo_root = Path(__file__).resolve().parent.parent.parent
    figures_dir = repo_root / "publication" / "results" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    manuscript_dir = repo_root / "publication" / "manuscripts"

    width, height = 1907, 861
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    fonts = get_fonts()

    # Colors
    c_black = "#000000"
    c_red = "#C00000"
    c_dark_green = "#1B5E20"
    c_yellow_bg = "#FFFF00"
    c_green_bg = "#00E676"  # Vibrant highlight green

    # -------------------------------------------------------------
    # 1. Section 1: Original Content
    # -------------------------------------------------------------
    draw_badge(draw, 45, 38, "Original Content", fonts["badge"], c_black)
    draw_arrow(draw, x=65, y_start=155, y_end=245, width=3, head_size=15)

    orig_line1 = "Concomitant medications included on an unknown date, atenolol tablet at a dose of 25 milligrams twice a"
    orig_line2 = "day via unknown route for unknown indication."

    draw.text((140, 140), orig_line1, fill=c_black, font=fonts["italic"])
    draw.text((140, 215), orig_line2, fill=c_black, font=fonts["italic"])

    # -------------------------------------------------------------
    # 2. Section 2: Model Output
    # -------------------------------------------------------------
    draw_badge(draw, 45, 310, "Model Output", fonts["badge"], c_red)
    draw_arrow(draw, x=65, y_start=435, y_end=525, width=3, head_size=15)

    # Model Output Line 1
    cur_x = 140
    y_m1 = 415
    cur_x += draw_styled_segment(draw, cur_x, y_m1, "Concomitant medications included on an ", fonts["regular"], c_black)
    cur_x += draw_styled_segment(draw, cur_x, y_m1, "<DATE>unknown", fonts["regular"], c_black, c_yellow_bg)
    cur_x += draw_styled_segment(draw, cur_x, y_m1, "</DATE>", fonts["regular"], c_red, c_yellow_bg)
    cur_x += draw_styled_segment(draw, cur_x, y_m1, " date, ", fonts["regular"], c_black)
    cur_x += draw_styled_segment(draw, cur_x, y_m1, "<CDRUG>atenolol</CDRUG>", fonts["regular"], c_black, c_yellow_bg)
    cur_x += draw_styled_segment(draw, cur_x, y_m1, " tablet at a", fonts["regular"], c_black)

    # Model Output Line 2
    cur_x = 140
    y_m2 = 490
    cur_x += draw_styled_segment(draw, cur_x, y_m2, "dose of ", fonts["regular"], c_black)
    cur_x += draw_styled_segment(draw, cur_x, y_m2, "<DOSE>25 milligrams twice a day</DOSE>", fonts["regular"], c_black, c_yellow_bg)
    cur_x += draw_styled_segment(draw, cur_x, y_m2, " via unknown route ", fonts["regular"], c_black)
    cur_x += draw_styled_segment(draw, cur_x, y_m2, "and", fonts["bold"], c_red)
    cur_x += draw_styled_segment(draw, cur_x, y_m2, " indication.", fonts["regular"], c_black)

    # -------------------------------------------------------------
    # 3. Section 3: Annotated Text
    # -------------------------------------------------------------
    draw_badge(draw, 45, 595, "Annotated Text", fonts["badge"], c_dark_green)

    # Annotated Text Line 1
    cur_x = 140
    y_a1 = 690
    cur_x += draw_styled_segment(draw, cur_x, y_a1, "Concomitant medications included on an unknown date, ", fonts["regular"], c_black)
    cur_x += draw_styled_segment(draw, cur_x, y_a1, "<CDRUG>atenolol</CDRUG>", fonts["regular"], c_black, c_green_bg)
    cur_x += draw_styled_segment(draw, cur_x, y_a1, " tablet at a dose of", fonts["regular"], c_black)

    # Annotated Text Line 2
    cur_x = 140
    y_a2 = 765
    cur_x += draw_styled_segment(draw, cur_x, y_a2, "<DOSE>25 milligrams twice a day</DOSE>", fonts["regular"], c_black, c_green_bg)
    cur_x += draw_styled_segment(draw, cur_x, y_a2, " via unknown route ", fonts["regular"], c_black)
    cur_x += draw_styled_segment(draw, cur_x, y_a2, "for unknown", fonts["bold"], c_dark_green)
    cur_x += draw_styled_segment(draw, cur_x, y_a2, " indication.", fonts["regular"], c_black)

    # Save to files
    out_fig_path = figures_dir / "figure2.png"
    out_manuscript_fig = manuscript_dir / "figure2.png"
    out_docx_img = manuscript_dir / "extracted_images" / "image_01.png"

    img.save(out_fig_path, "PNG", dpi=(300, 300))
    img.save(out_manuscript_fig, "PNG", dpi=(300, 300))
    img.save(out_docx_img, "PNG", dpi=(300, 300))

    print(f"Figure 2 successfully generated and saved to:\n  - {out_fig_path}\n  - {out_manuscript_fig}\n  - {out_docx_img}")


if __name__ == "__main__":
    main()
