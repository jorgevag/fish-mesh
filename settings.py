from typing import Dict
from dataclasses import dataclass
import dacite
from pathlib import Path
import json


DEFAULT_SETTINGS_PATH = Path.cwd() / 'fish-mesh-settings.json'


class SettingsError(Exception):
    pass


@dataclass
class Settings:
    measure_box_width: float = 42.0
    measure_box_height: float = 29.6
    measure_box_margin_ratio: float = 0.1  # to allow showing the entire head of fish placed along the edge
    font_size: int = 16
    point_size: int = 1
    show_mini_window_on_start: bool = True
    draw_color: str = "#ffff00"  # yellow

    def validate(self):
        if not self.measure_box_width > 0:
            raise SettingsError("'Measure box width' must be larger than 0")
        if not self.measure_box_height > 0:
            raise SettingsError("'Measure box height' must be larger than 0")
        if not self.measure_box_height > 0:
            raise SettingsError("'Measure box height' must be larger than 0")
        if not self.point_size > 0:
            raise SettingsError("'Point size' must be larger than 0")
        if not self.measure_box_margin_ratio > 0:
            raise SettingsError("'Measure box margin ratio' must be larger than 0")

    @staticmethod
    def from_dict(d: Dict):
        return dacite.from_dict(
            data_class=Settings, data=d, config=dacite.Config(strict=True)
        )

    @staticmethod
    def from_file(path: Path):
        with open(path) as f:
            return Settings.from_dict(json.loads(f.read()))


SETTING_DESCRIPTIONS = dict(
    measure_box_width=(
        "The width of the reference box. This number will be used"
        "\ntogether with the measure box height to calculate the"
        "\nlength of the drawn lines within the measurement box"
    ),
    measure_box_height=(
        "The height of the reference box. This number will be used"
        "\ntogether with the measure box width to calculate the"
        "\nlength of the drawn lines within the measurement box"
    ),
    measure_box_margin_ratio=(
        "This option allows you to specify how much of the adjusted"
        "\nimage outside the bounding box that will be displayed."
        "\nThis is given as a ratio of the size of the bounding box,"
        "\nsuch that 0.1 means that 10 % of the shown image will be"
        "\noutside of the bounding box after the adjustment. A value"
        "\nof 0 will only include what is inside the bounding box."
    ),
    font_size=(
        "The font size of the shown length measurements"
    ),
    point_size_pixels=(
        "The size of the points (in pixels) used for bounding box corners and"
        " drawn rulers."
    ),
    draw_color=(
        "The color of everything drawn within the program."
        "\nFor simplicity this is limited to a single color."
    ),
)