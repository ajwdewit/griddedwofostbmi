import os, sys
import collections

import xarray

import pcse
from pcse.base import WeatherDataProvider
from pcse.util import check_date

class WFLOWWeatherDataProvider(WeatherDataProvider):
    """Class for reading Meteodata in WFLOW NetCDF structure.
    """
    config = None
    description = "WeatherDataProvider for WFLOW NetCDF data."
    active_day = None
    active_layers = {}
    weather_data_container = collections.namedtuple("WeatherDataContainer","TMIN TMAX TEMP DTEMP RAIN ET0, ES0, E0, IRRAD")

    def __init__(self, config):
        self.config = config.weather_variables
        if not os.path.exists(self.config.location):
            msg = f"Input file {self.config.location} does not exists!"
            raise RuntimeError(msg)

    def _read_new_layer(self, day):
        self.active_layers = {}
        with xarray.open_dataset(self.config.location) as ds:
            ds_oneday = ds.sel(time=day)
            ds_oneday.read()
            self.active_layers = \
                dict(TEMP=ds_oneday.data_vars["TEMP"],
                     ET0=ds_oneday.data_vars["PET"],
                     ES0=ds_oneday.data_vars["PET"],
                     E0=ds_oneday.data_vars["PET"],
                     TMIN=self._create_dummy_TMIN(day, ds_oneday.data_vars["TEMP"]),
                     TMAX=self._create_dummy_TMAX(day, ds_oneday.data_vars["TEMP"]),
                     IRRAD=self._create_dummy_IRRAD(ds_oneday.data_vars["PET"]),
                     DTEMP=ds_oneday.data_vars["TEMP"] + 2.5,
                     RAIN=ds_oneday.data_vars["TEMP"])

    def __call__(self, day, row, col):
        day = check_date(day)
        if day != self.active_day:
            self._read_new_layer(day)
            self.active_day = day

        meteo_vars = {}
        for varname, meteo_variable in self.active_layers.items():
            meteo_vars[varname] = meteo_variable[row, col]
        return self.weather_data_container(**meteo_vars)

    def _create_dummy_TMIN(self, day, TEMP):
        return TEMP - 5.

    def _create_dummy_TMAX(self, day, TEMP):
        return TEMP + 5.

    def _create_dummy_IRRAD(self, day, ET0):
        return ET0 * 2.45E6  # Derive directly from ET0 * latent heat for vaporization
