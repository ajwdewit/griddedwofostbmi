from pathlib import Path
from itertools import product
import time

import numpy as np
import yaml
from dotmap import DotMap
import rasterio

from pcse.fileinput import YAMLCropDataProvider
from pcse.util import WOFOST71SiteDataProvider
from pcse.base import ParameterProvider

from .dataproviders import WFLOWWeatherDataProvider, read_agromanagement
from .engine import GridAwareEngine


def check_grid_size(conf, grid):
    gd = conf.maps.metadata
    if grid.shape != (gd.nrows, gd.ncols):
        msg = "Grid shape not equal to definition in config file!"
        raise RuntimeError


def read_config_file(config_file):
    config_file = Path(config_file).resolve()
    if config_file.is_absolute():
        config_file = config_file.resolve()
    else:
        top_dir = Path(__file__).parent.parent
        config_file = top_dir / "config" / config_file
    if not config_file.exists():
        msg = f"Cannot find GriddedWOFOSTBMI config file at: {config_file}"
        raise RuntimeError(msg)

    with config_file.open() as fp:
        conf = yaml.safe_load(fp.read())
    return DotMap(conf)


class GriddedWOFOSTBMI:

    def __init__(self, *args, **kwargs):
        self.initialize(*args, **kwargs)

    def initialize(self, config_file="gridded_wofost.yaml"):
        t1 = time.time()
        self.config = read_config_file(config_file)

        # Layer inputs for AgroManagement
        with rasterio.open(self.config.maps.AEZ_map.location) as ds:
            aez_map = ds.read(1)
            aez_map[aez_map < 0] = np.NaN
            check_grid_size(self.config, aez_map)
        with rasterio.open(self.config.maps.crop_rotation_map.location) as ds:
            crop_rotation_map = ds.read(1)
            crop_rotation_map[crop_rotation_map < 0] = np.NaN
            check_grid_size(self.config, crop_rotation_map)

        # Crop, site parameters and soil grid
        crop_parameters = YAMLCropDataProvider(fpath=self.config.crop_parameters.location)
        site_parameters = WOFOST71SiteDataProvider(WAV=10, CO2=360)
        with rasterio.open(self.config.maps.rooting_depth.location) as ds:
            rooting_depth = ds.read(1)
            rooting_depth[rooting_depth < 0] = np.NaN
            check_grid_size(self.config, rooting_depth)

        # Weather from WFLOW NetCDF files
        self.WFLOWWeatherDataProvider = WFLOWWeatherDataProvider(self.config)

        # initialize object grid for storing WOFOST results
        self.WOFOSTgrid = np.ndarray(shape=aez_map.shape, dtype=np.object)

        nrows, ncols = aez_map.shape
        p_row = None
        for i, (row, col) in enumerate(product(range(nrows), range(ncols))):
            if row != p_row:
                p_row = row
                print(f"Initializing row: {row}")
            if row == 15:
                break
            crop_rotation_type = crop_rotation_map[row, col]
            aez = aez_map[row, col]
            if crop_rotation_type not in self.config.maps.crop_rotation_map.relevant_crop_rotations:
                continue
            if aez not in self.config.maps.AEZ_map.relevant_AEZ:
                continue
            agro = read_agromanagement(self.config, aez, crop_rotation_type)
            soil_parameters = {"RDMSOL": rooting_depth[row, col], "SM0": 0.4, "SMFCF": 0.25, "SMW": 0.1, "CRAIRC": 0.04}
            params = ParameterProvider(sitedata=site_parameters, cropdata=crop_parameters, soildata=soil_parameters)
            wofsim = GridAwareEngine(row=row, col=col, parameterprovider=params,
                                     weatherdataprovider=self.WFLOWWeatherDataProvider,
                                     agromanagement=agro, config="Wofost71_PP.conf")
            self._check_start_end_date(wofsim, row, col, aez, crop_rotation_type)
            self.WOFOSTgrid[row, col] = wofsim
        print(f"Initializing took {time.time() - t1} seconds")

    def _check_start_end_date(self, wofsim, row, col, aez, crop_rotation_type):
        """Checks the start/end date of a given model instance with the global configuration
        """
        if wofsim.start_date != self.config.runtime.start_date:
            msg = f"Start date for model {wofsim.start_date} not equal to " \
                  f"configuration start date {self.config.runtime.start_date}! " \
                  f"At row/col {row}/{col}, AEZ {aez} and crop_rotation_type {crop_rotation_type}"
            raise RuntimeError(msg)

        if wofsim.end_date != self.config.runtime.end_date:
            msg = f"End date for model {wofsim.end_date} not equal to " \
                  f"configuration end date {self.config.runtime.end_date}! " \
                  f"At row/col {row}/{col}, AEZ {aez} and crop_rotation_type {crop_rotation_type}"
            raise RuntimeError(msg)

    def update(self):
        for wofsim in self.WOFOSTgrid.flatten():
            if wofsim is not None:
                wofsim.run()

    def get_current_time(self):
        for wofsim in self.WOFOSTgrid.flatten():
            if wofsim is not None:
                return wofsim.day

    def get_start_time(self):
        for wofsim in self.WOFOSTgrid.flatten():
            if wofsim is not None:
                return wofsim.start_date

    def get_end_time(self):
        for wofsim in self.WOFOSTgrid.flatten():
            if wofsim is not None:
                return wofsim.end_date

    def get_time_step(self):
        return 1.0

    def get_time_units(self):
        return "days"

    def get_input_var_names(self):
        return ["RFTRA"]

    def get_output_var_names(self):
        return ["LAI", "RD"]

    def get_var_units(self, varname):
        raise NotImplementedError()

    def get_value(self, varname, dest_array):
        if dest_array.shape != self.WOFOSTgrid.shape:
            msg = "WOFOST simulation grid and output array not the same size!"
            raise RuntimeError(msg)
        nrows = self.config.maps.metadata.nrows
        ncols = self.config.maps.metadata.ncols
        for row, col in product(range(nrows), range(ncols)):
            wofsim = self.WOFOSTgrid[row, col]
            if wofsim is None:
                continue
            value = wofsim.get_variable(varname)
            try:
                value = float(value)
            except (ValueError, TypeError) as e:
                value = np.NaN
            dest_array[row, col] = value
        print(1)
