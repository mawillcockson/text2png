"""Takes a text file and uses Pillow to generate PNGs of those lines of text"""
import math
import sys
from pathlib import Path
from re import compile as re_compile
from typing import List, NewType, Optional, Tuple, Union, NamedTuple
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from functools import reduce
from numbers import Number
from warnings import warn

from matplotlib.font_manager import FontProperties, findfont
from PIL import Image, ImageDraw, ImageFont, ImageColor
from PIL.ImageColor import getrgb

Size = NamedTuple("Size", width=Number, height=Number)
Position = NamedTuple("Position", x=Number, y=Number)

default_font = "KanjiStrokeOrders"
default_output_dir = Path("./output")
default_canvas_size = Size(1024, 1024)
default_padding = 0.10
default_background = "white"
default_text_color = "black"


def assign_path(text: str, dir: Union[Path, str]) -> Path:
    proper_dir = Path(dir)
    if proper_dir.exists() and not proper_dir.is_dir():
        raise FileExistsError(f"'{proper_dir}' is not a directory")
    elif proper_dir.exists():
        proper_path = proper_dir / (text + ".png")
    else:
        proper_dir.mkdir()
        proper_path = proper_dir / (text + ".png")

    try:
        proper_path.touch()
    except OSError as err:
        raise Exception(
            "Filesystem error likely prevented using a particular filename"
        ) from err

    return proper_path.resolve()


def center_text_position(
    text_size: Size, canvas_size: Size, padding: float
) -> Position:
    padding_width = padding * canvas_size.width / 2
    padding_height = padding * canvas_size.height / 2
    leftover_width = canvas_size.width - text_size.width - (padding_width * 2)
    leftover_height = canvas_size.height - text_size.height - (padding_height * 2)
    if leftover_height < 0 or leftover_width < 0:
        raise ValueError("Calculation error: can't size text")

    x = math.floor((leftover_width / 2) + padding_width)
    y = math.floor((leftover_height / 2) + padding_height)
    # Pillow's coordinates have 0,0 in the upper-left corner, and text is drawn
    # to the down and right of the point given
    return Position(x, y)


def generate_png(
    text: str,
    font: ImageFont,
    canvas_size: Size,
    padding: int,
    background: ImageColor,
    fill_color: ImageColor,
) -> Image:
    canvas = Image.new("RGBA", canvas_size, background)
    draw = ImageDraw.Draw(canvas)
    text_size = Size(*font.getsize(text=text))
    text_position = center_text_position(
        text_size=text_size, canvas_size=canvas_size, padding=padding
    )
    draw.text(xy=text_position, text=text, fill=fill_color, font=font)
    # Draws a circle to show text_position
    #draw.ellipse(xy=[text_position.x-3,text_position.y-3,text_position.x+3,text_position.y+3], fill="black")
    return canvas


def get_lines(text_file: Union[Path, str]) -> List[str]:
    """Returns a list of the lines from a file that aren't empty, and don't
    have a '#' as the first non-whitespace character"""
    text_path = Path(text_file)
    if not text_path.is_file():
        raise Exception(f"'{text_path}' is not a file")
    comment_or_empty = re_compile(r"^(\s*#.*)|(\s+)$")
    return [
        line
        for line in text_path.read_text(encoding="utf-8").splitlines()
        if line and (not comment_or_empty.search(line))
    ]


def parse_size(size: str) -> Size:
    size_re = re_compile(r"^(?P<width>\d+)x(?P<height>\d+)$")
    match = size_re.match(size)
    if not match:
        raise ArgumentTypeError(f"Bad size specification: {size}")
    width = int(match.group("width"))
    height = int(match.group("height"))
    return Size(width, height)


def get_max_text_size(lines: List[str], font: str) -> Size:
    """Return the approximate size in pixels the largest dimensions of any line of text would be if the font size was 1pt"""
    font_file = findfont(font)
    font_image = ImageFont.truetype(font_file, size=100)
    text_sizes = map(font_image.getsize, lines)
    tuple_max = lambda a, b: (max(a[0], b[0]), max(a[1], b[1]))
    max_size_at_100 = reduce(tuple_max, text_sizes)
    return Size(max_size_at_100[0] / 100, max_size_at_100[1] / 100)


def get_font(
    lines: List[str], canvas_size: Size, padding: int, font_name: Optional[str] = None
) -> ImageFont:
    max_text_size = get_max_text_size(lines=lines, font=font_name)
    usable_width = canvas_size.width - padding * canvas_size.width
    usable_height = canvas_size.height - padding * canvas_size.height
    if usable_height < 10:
        warn(f"The text will have a height of {usable_height}px")
    if usable_width < 10:
        warn(f"The text will have a width of {usable_width}px")
    # By what scale factor can I multiply a rectangle with max_text_size dimensions to completely fill my useable area?
    # If I made the height as large as the useable height, would the width be larger than the useable width?
    scale_factor = usable_height / max_text_size.height
    if scale_factor * max_text_size.width > usable_width:
        font_size = math.floor(usable_width / max_text_size.width)
    else:
        font_size = math.floor(scale_factor)
    font_file = findfont(font_name)
    font_image = ImageFont.truetype(font_file, size=font_size)
    return font_image


def main(
    text_file: Path,
    output_dir: Path = default_output_dir,
    font: str = default_font,
    canvas_size: Size = default_canvas_size,
    padding: float = default_padding,
    background: str = default_background,
    text_color: str = default_text_color,
) -> None:
    background_color = getrgb(background)

    fill_color = getrgb(text_color)

    lines = get_lines(text_file)

    image_font = get_font(lines, canvas_size, padding, font)

    for text in lines:
        generate_png(
            text=text,
            font=image_font,
            canvas_size=canvas_size,
            padding=padding,
            background=background_color,
            fill_color=fill_color,
        ).save(
            fp=assign_path(text, output_dir), format="PNG",
        )


if __name__ == "__main__":
    parser = ArgumentParser(description="Generates images of characters")

    def str_to_dir(path: str) -> Path:
        path = Path(path)
        if path.is_dir():
            return path
        else:
            raise ArgumentTypeError("PATH needs to be a directory that exists")

    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        required=True,
        help="File containing lines of text to make pictures of",
    )
    parser.add_argument(
        "-d",
        "--output-dir",
        type=str_to_dir,
        default=default_output_dir,
        help="Directory in which to output pictures",
    )
    parser.add_argument("--font", default=default_font, help="Font to use for text")
    parser.add_argument(
        "--size",
        type=parse_size,
        default=default_canvas_size,
        help="Size to make all character images",
    )
    parser.add_argument(
        "--padding",
        type=float,
        default=default_padding,
        help="The percentage of the canvas dimensions to use as a blank border",
    )
    parser.add_argument(
        "--background", default=default_background, help="Color for the background"
    )
    parser.add_argument(
        "--text-color", default=default_text_color, help="Color to use for the text"
    )

    args = parser.parse_args()
    main(
        text_file=args.file,
        output_dir=args.output_dir,
        font=args.font,
        canvas_size=args.size,
        padding=args.padding,
        background=args.background,
        text_color=args.text_color,
    )
