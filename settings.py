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
    font_size: int = 16
    point_size_relative_to_monitor_width: float = 0.0001  # 0.0025
    draw_color: str = "#ffff00"  # yellow
    measure_box_margin_rel = 0.1  # to allow showing the entire head of fish placed along the edge

    def validate(self):
        if not self.measure_box_width > 0:
            raise SettingsError("'Measure box width' must be larger than 0")
        if not self.measure_box_height > 0:
            raise SettingsError("'Measure box height' must be larger than 0")
        if not self.measure_box_height > 0:
            raise SettingsError("'Measure box height' must be larger than 0")
        if not self.point_size_relative_to_monitor_width > 0:
            raise SettingsError("'Point size relative to monitor width' must be larger than 0")

    @staticmethod
    def from_dict(d: Dict):
        return dacite.from_dict(
            data_class=Settings, data=d, config=dacite.Config(strict=True)
        )

    @staticmethod
    def from_file(path: Path):
        with open(path) as f:
            return Settings.from_dict(json.loads(f.read()))
