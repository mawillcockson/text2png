"""Takes a text file and uses Pillow to generate PNGs of those lines of text"""
import math
import sys
from collections import namedtuple
from pathlib import Path
from re import compile as re_compile
from typing import List, NewType, Optional, Tuple, Union

from invoke import Collection, Config, Context, Program, task
from invoke.config import merge_dicts
from invoke.watchers import Responder
from matplotlib.font_manager import FontProperties, findfont
from PIL import Image, ImageColor, ImageDraw, ImageFont

PROG_NAME = sys.argv[0]
default_font = "KanjiStrokeOrders"
default_output_dir = "./output"
default_canvas_size = "500x500"
default_padding = 10
default_background = "white"
default_text_color = "black"

Size = namedtuple("Size", "height, width")
Position = namedtuple("Position", "x, y")


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


def center_text_position(text_size: Size, canvas_size: Size, padding: float) -> Position:
    padding_width = padding * canvas_size.width
    padding_height = padding * canvas_size.height
    leftover_width = canvas_size.width - text_size.width - padding_width
    leftover_height = canvas_size.height - text_size.height - padding_height
    if leftover_height < 0 or leftover_width < 0:
        raise ValueError("Calculation error: can't size text")

    x = math.floor(leftover_width / 2) + padding_width
    y = math.floor(leftover_height / 2) + padding_height
    # Pillow's coordinates have 0,0 in the upper-left corner, and text is drawn to the up and
    # right of the point given, so the y-value needs to be "flipped" about the
    # horizontal middle of the image
    y_flipped = canvas_size.height - y
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
    text_position = center_text_position(text_size, canvas_size, padding)
    draw.text(xy=text_position, text=text, fill=fill_color, font=font)
    return canvas


def get_lines(text_file: str) -> List[str]:
    text_path = Path(text_file)
    if not text_path.is_file():
        raise Exception(f"'{text_path}' is not a file")

    return text_path.read_text().splitlines()


def parse_size(size: str) -> Size:
    size_re = re_compile(r"^(?P<width>\d+)x(?P<height>\d+)$")
    match = size_re.match(size)
    if not match:
        raise ValueError(f"Bad size specification: {size}")
    width = int(match.group('width'))
    height = int(match.group('height'))
    return Size(width, height)


def get_max_text_size(lines: List[str], font_props: FontProperties) -> Size:
    pass


def get_font(
    lines: List[str], canvas_size: Size, padding: int, font_name: Optional[str] = None
) -> ImageFont:
    font_file = findfont(font_name)
    font_image = ImageFont.truetype(font_file, size=100)
    return font_image


def default_task(
    ctx: Context,
    text_file: str,
    output_dir: Optional[Path] = None,
    font: Optional[str] = None,
    size: Optional[str] = None,
    padding: Optional[int] = None,
    background: Optional[str] = None,
    text_color: Optional[str] = None,
) -> None:
    if not output_dir:
        output_dir = ctx.output.default

    if not size:
        size = ctx.style.size

    canvas_size = parse_size(size)

    if not font:
        font = ctx.font.default

    if padding == None:
        padding = ctx.style.padding
    
    padding = float(padding)

    if not background:
        background = ctx.style.background

    background_color = ImageColor.getrgb(background)

    if not text_color:
        text_color = ctx.style.text_color

    fill_color = ImageColor.getrgb(text_color)

    lines = get_lines(text_file)

    image_font = get_font(lines, canvas_size, padding, font)

    for text in lines:
        return generate_png(
            text=text,
            font=image_font,
            canvas_size=canvas_size,
            padding=padding,
            background=background_color,
            fill_color=fill_color,
        ).save(
            fp=assign_path(text), format="PNG",
        )


if __name__ == "__main__":
    namespace = Collection()
    namespace.configure(
        {
            "output": {"default": default_output_dir},
            "font": {"default": default_font},
            "style": {
                "size": default_canvas_size,
                "padding": default_padding,
                "background": default_background,
                "text_color": default_text_color,
            },
        }
    )
    namespace.add_task(task(default_task, post=[]), default=True)
    for i, name in enumerate(namespace.tasks["atask-default"].post):
        namespace.tasks["atask-default"].post[i] = task(name)
        namespace.add_task(task(name))

    class SetupConfig(Config):
        prefix: str = PROG_NAME

        @staticmethod
        def global_defaults():
            base_defaults = Config.global_defaults()
            overrides = {
                "tasks": {"collection_name": PROG_NAME},
            }
            return merge_dicts(base=base_defaults, updates=overrides)

    program = Program(
        name=PROG_NAME, namespace=namespace, config_class=SetupConfig, version="0.0.1"
    )
    program.run()
