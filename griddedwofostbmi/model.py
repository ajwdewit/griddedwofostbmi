import os
from pathlib import Path

import yaml
from dotmap import DotMap
import rasterio
from bmipy import Bmi

import pcse
from pcse.fileinput import YAMLCropDataProvider


class GriddedWOFOSTBMI():

    def __init__(self, *args, **kwargs):
        self.initialize(*args, **kwargs)

    def initialize(self, config_file="gridded_wofost.yaml"):
        conf = self._read_config_file(config_file)
        with rasterio.open(conf.maps.AEZ_map.location) as ds:
            aez_map = ds.read(1)
        with rasterio.open(conf.maps.crop_rotation_map.location) as ds:
            crop_rotation_map = ds.read(1)
        crop_parameters = YAMLCropDataProvider(fpath=conf.crop_parameters)



        print(1)

    def _read_config_file(self, config_file):
        config_file = Path(config_file).resolve()
        if config_file.is_absolute():
            config_file = os.path.normpath(config_file)
        else:
            top_dir = Path(__file__).parent.parent
            config_file = top_dir / "config" / config_file
        if not config_file.exists():
            msg = f"Cannot find GriddedWOFOSTBMI config file at: {config_file}"
            raise RuntimeError(msg)

        with config_file.open() as fp:
            conf = yaml.load(fp.read())
        return DotMap(conf)

if __name__ == "__main__":
    g = GriddedWOFOSTBMI()