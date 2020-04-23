"""Takes a text file and uses Pillow to generate PNGs of those lines of text"""
import logging
import math
import sys
from argparse import ArgumentParser, ArgumentTypeError, Namespace
from functools import reduce
from numbers import Number
from pathlib import Path
from re import compile as re_compile
from typing import List, NamedTuple, NewType, Optional, Tuple, Union, Dict
from warnings import warn
import atexit

from matplotlib.font_manager import FontProperties, findfont
from PIL import Image, ImageColor, ImageDraw
from PIL.ImageFont import ImageFont, truetype as PILtruetype
from PIL.ImageColor import getrgb

Num = Union[int, float]
LogLevel = Optional[Union[int, str, bool]]
SPath = Union[str, Path]


class Size(NamedTuple):
    width: Num
    height: Num


class Position(NamedTuple):
    x: Num
    y: Num


default_font = "KanjiStrokeOrders"
default_output_dir = Path("./output")
default_canvas_size = Size(1024, 1024)
default_padding = 0.10
default_background = "white"
default_text_color = "black"
default_log_level: LogLevel = logging.WARNING


# Regexes
size_re = re_compile(r"^(?P<width>\d+)x(?P<height>\d+)$")
comment_re = re_compile(r"^\s*(#|＃).*$")
blank_re = re_compile(r"^\s+$")


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

    return proper_path.expanduser().resolve()


def center_text_position(
    text_size: Size, canvas_size: Size, padding: float
) -> Position:
    padding_width = padding * canvas_size.width / 2
    padding_height = padding * canvas_size.height / 2
    leftover_width = canvas_size.width - text_size.width - (padding_width * 2)
    leftover_height = canvas_size.height - text_size.height - (padding_height * 2)
    if leftover_height < 0 or leftover_width < 0:
        raise ValueError("Calculation error: text too big for canvas")

    x = math.floor((leftover_width / 2) + padding_width)
    y = math.floor((leftover_height / 2) + padding_height)
    # Pillow's coordinates have 0,0 in the upper-left corner, and text is drawn
    # to the down and right of the point given
    return Position(x, y)


def generate_png(
    text: str,
    font: ImageFont,
    canvas_size: Size,
    padding: Num,
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
    # draw.ellipse(xy=[text_position.x-3,text_position.y-3,text_position.x+3,text_position.y+3], fill="black")
    return canvas


def not_comment_or_blank(string: str) -> bool:
    return not bool(
        comment_re.search(string) or blank_re.search(string) or string == ""
    )


def which_exist(names: List[str], directory: Union[Path, str]) -> Dict[str, Path]:
    """Checks which file names are already taken in a directory,
    and raises an error if it wasn't a file that took the name"""
    dir_path = Path(directory)
    if not (dir_path.is_dir() and dir_path.exists()):
        raise ValueError(f"'{dir_path}' must be a directory")
    dir_contents = list(dir_path.iterdir())
    non_files = [str(path) for path in filter(lambda f: not f.is_file(), dir_contents)]
    colliding_names = [name for name in names if name in non_files]
    for name in colliding_names:
        logging.error(
            f"'{name}' can't be created because there's something that's not a picture in the directory '{directory}' that already has that name"
        )
    if colliding_names:
        colliding_list = "\n".join(colliding_names)
        raise FileExistsError(
            f"These are names of files that would be created in '{directory}', but can't:\n{colliding_list}"
        )
    return {file.name: file for file in dir_contents}


def get_characters(
    text_file_or_list: Union[Path, str, List[str]], directory: SPath, clobber: bool
) -> List[str]:
    """Returns a list of the lines from a file that aren't empty, and don't
    have a '#' as the first non-whitespace character
    Alternatively, takes a list of strings"""
    if isinstance(text_file_or_list, list):
        lines = text_file_or_list
    elif isinstance(text_file_or_list, str) or isinstance(text_file_or_list, Path):
        text_path = Path(text_file_or_list)
        if not text_path.is_file():
            raise Exception(f"'{text_path}' is not a file")
        lines = text_path.read_text().splitlines()
    else:
        raise TypeError(
            f"text_file_or_list must be a path or list of characters; got:\n{text_file_or_list}"
        )

    characters = list(filter(not_comment_or_blank, lines))
    # Check to see if any lines clash with existing directory or non-file names
    dir_contents = which_exist(
        names=[character + ".png" for character in characters], directory=directory
    )
    # If we're clobbering, don't filter; otherwise, remove any lines that already have pictures generated
    if clobber:
        filtered_lines = characters
    else:
        unique_characters = set(characters)
        dir_set = set(dir_contents.keys())
        for line in unique_characters & dir_set:
            logging.info(f"Not clobbering '{line}.png'")

        filtered_lines = list(unique_characters - dir_set)

    return filtered_lines


def parse_size(size: str) -> Size:
    match = size_re.match(size)
    if not match:
        raise ArgumentTypeError(f"Bad size specification: {size}")
    width = int(match.group("width"))
    height = int(match.group("height"))
    return Size(width, height)


def get_max_text_size(lines: List[str], font: str) -> Size:
    """Return the approximate size in pixels of the smallest bounding box that can enclose every line of text at a font size of 1pt"""
    font_file = findfont(font)
    font_image = PILtruetype(font_file, size=1000)
    text_sizes = map(font_image.getsize, lines)
    tuple_max = lambda a, b: Size(max(a[0], b[0]), max(a[1], b[1]))
    max_size_at_1000 = reduce(tuple_max, text_sizes, Size(0, 0))
    return Size(max_size_at_1000.width / 1000, max_size_at_1000.height / 1000)


def get_font(
    lines: List[str], canvas_size: Size, padding: Num, font_name: str = default_font,
) -> ImageFont:
    max_text_size = get_max_text_size(lines=lines, font=font_name)
    if max_text_size.height <= 0 or max_text_size.width <= 0:
        logging.warn("No text will be drawn")
        font_file = findfont(font_name)
        return PILtruetype(font_file, size=1)

    usable_width = canvas_size.width - padding * canvas_size.width
    usable_height = canvas_size.height - padding * canvas_size.height
    if usable_height < 10:
        logging.warn(f"The text will have a height of {usable_height}px")
    if usable_width < 10:
        logging.warn(f"The text will have a width of {usable_width}px")
    # By what scale factor can I multiply a rectangle with max_text_size dimensions to completely fill my useable area?
    # If I made the height as large as the useable height, would the width be larger than the useable width?
    max_font_size_height = usable_height / max_text_size.height
    max_font_size_width = usable_width / max_text_size.width
    # Which scale factor won't overflow the useable area?
    # NOTE: Subtracting 1 because getsize(text) rounds up
    font_size = math.floor(min(max_font_size_height, max_font_size_width)) - 1
    font_file = findfont(font_name)
    font_image = PILtruetype(font_file, size=font_size)
    return font_image


def setup_logging(level: Optional[LogLevel] = default_log_level) -> None:
    if level == False:
        return None
    elif not level:
        logging.basicConfig(format="%(message)s", level=default_log_level)
    else:
        logging.basicConfig(format="%(message)s", level=level)


def error(message: str) -> Exception:
    logging.error(message)
    return Exception(message)


def main(
    file_or_list: Union[SPath, List[str]],
    output_dir: SPath = default_output_dir,
    log_level: Optional[LogLevel] = default_log_level,
    font: Optional[Union[str, ImageFont]] = default_font,
    size: Optional[Union[str, Size]] = default_canvas_size,
    padding: Optional[Union[str, Num]] = default_padding,
    background: Optional[str] = default_background,
    text_color: Optional[str] = default_text_color,
    clobber: Optional[bool] = False,
) -> List[Path]:
    setup_logging(level=log_level)

    if not size:
        canvas_size = default_canvas_size
    elif isinstance(size, Size):
        canvas_size = size
    else:
        canvas_size = parse_size(size)

    padding_or_default = default_padding if padding == None else padding
    try:
        pad = float(padding_or_default)
    except ValueError as err:
        raise error(
            f"Expected padding format to be like '0.1', instead got '{padding}'"
        )

    output_directory = Path(output_dir or default_output_dir)

    if not output_directory.exists():
        try:
            output_directory.mkdir()
        except Exception as err:
            raise error(f"Can't make directory '{output_directory}'")

    lines = get_characters(
        text_file_or_list=file_or_list,
        directory=output_dir,
        clobber=(clobber if clobber != None else False),
    )

    if not lines:
        logging.info("No pictures will be generated")
        return list()

    if isinstance(font, ImageFont):
        image_font = font
    else:
        image_font = get_font(
            lines=lines,
            canvas_size=canvas_size,
            padding=pad,
            font_name=(font or default_font),
        )

    background_color = getrgb(color=(background or default_background))

    fill_color = getrgb(color=(text_color or default_text_color))

    for text in lines:
        generate_png(
            text=text,
            font=image_font,
            canvas_size=canvas_size,
            padding=pad,
            background=background_color,
            fill_color=fill_color,
        ).save(
            fp=assign_path(text=text, dir=output_directory), format="PNG",
        )

    return [output_directory / (f"{line}.png") for line in lines]


if __name__ == "__main__":
    # setup_logging()

    parser = ArgumentParser(description="Generates images of characters")

    def str_to_dir(path: str) -> Path:
        dir = Path(path)
        if dir.is_dir():
            return dir
        else:
            raise ArgumentTypeError(f"{dir} needs to be a directory that exists")

    def create_if_absent(path: str) -> Path:
        dir = Path(path)
        if not dir.exists():
            dir.mkdir()

        if not dir.is_dir():
            raise ArgumentTypeError(f"'{dir}' must be a directory")

        return dir

    def parse_log_level(level: str) -> int:
        levels = {
            "critical": logging.CRITICAL,
            "error": logging.ERROR,
            "warning": logging.WARNING,
            "info": logging.INFO,
            "debug": logging.DEBUG,
        }
        if not level.lower() in levels:
            raise ArgumentTypeError(
                f"'{level}' isn't one of: {' '.join(levels.keys())}"
            )
        return levels[level.lower()]

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
        type=create_if_absent,
        default=default_output_dir,
        help="Directory in which to output pictures",
    )
    parser.add_argument("--font", default=default_font, help="Font to use for text")
    parser.add_argument(
        "--size",
        type=parse_size,
        default=default_canvas_size,
        help="Size in pixels to make all character images (e.g. 500x500)",
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
    parser.add_argument(
        "--clobber",
        action="store_true",
        help="If passed, will overwrite existing files; otherwise, nothing is clobbered",
    )
    parser.add_argument(
        "--log",
        default=default_log_level,
        type=parse_log_level,
        help="Verbosity/log level",
    )

    atexit.register(print, parser.format_help())

    args = parser.parse_args()
    main(
        file_or_list=args.file,
        output_dir=args.output_dir,
        log_level=args.log,
        font=args.font,
        size=args.size,
        padding=args.padding,
        background=args.background,
        text_color=args.text_color,
        clobber=args.clobber,
    )
