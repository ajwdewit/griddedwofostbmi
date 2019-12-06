# -*- coding: utf-8 -*-
# Copyright (c) 2019 Wageningeni Environmental Research, Wageningen-UR
# Allard de Wit (allard.dewit@wur.nl), December 2019
import os, sys
import collections
from pathlib import Path

import xarray
import numpy as np

from pcse.base import WeatherDataProvider
from pcse.util import check_date
from pcse.fileinput import YAMLAgroManagementReader


def read_agromanagement(conf, aez, crop_rotation_type, _cache={}):
    """Reads the proper agromanagement file for given EAZ and crop rotation type

    :param conf: the configuration file specifying path locations
    :param aez: the AEZ number
    :param crop_rotation_type: the crop rotation type number
    :return: a AgroManagement definition in YAML
    """
    if (aez, crop_rotation_type) not in _cache:
        agro_location = Path(conf.agromanagement_definitions.location)
        agro_definition_fname = agro_location / ("AEZ_%03i" % aez) / ("rotation_type_%02i.yaml" % crop_rotation_type)
        agro_definition = YAMLAgroManagementReader(agro_definition_fname)
        _cache[(aez, crop_rotation_type)] = agro_definition
    else:
        agro_definition = _cache[(aez, crop_rotation_type)]

    return agro_definition


class WFLOWWeatherDataProvider(WeatherDataProvider):
    """Class for reading Meteodata in WFLOW NetCDF structure.
    """
    config = None
    latitude = None
    longitude = None
    description = "WeatherDataProvider for WFLOW NetCDF data."
    active_day = None
    active_layers = {}
    weather_data_container = collections.namedtuple("WeatherDataContainer","LAT LON DAY TMIN TMAX TEMP DTEMP RAIN ET0, ES0, E0, IRRAD")

    def __init__(self, config):
        self.config = config
        if not os.path.exists(self.config.weather_variables.location):
            msg = f"Input file {self.config.weather_variables.location} does not exists!"
            raise RuntimeError(msg)

        with xarray.open_dataset(self.config.weather_variables.location) as ds:
            gd = self.config.maps.metadata
            if ds.lat.shape != (gd.nrows,) and ds.lon.shape != (gd.ncols,):
                raise RuntimeError("Input weather grid not equal to grid definition in configuration")

            # Store lat/lon for further use
            self.latitude = np.array(ds.lat)
            self.longitude = np.array(ds.lon)

    def _read_new_layer(self, day):
        with xarray.open_dataset(self.config.weather_variables.location) as ds:
            ds_oneday = ds.sel(time=day)
            ds_oneday.load()
            self.active_layers = \
                dict(TEMP=ds_oneday.data_vars["TEMP"],
                     ET0=ds_oneday.data_vars["PET"]/10.,
                     ES0=ds_oneday.data_vars["PET"]/10.,
                     E0=ds_oneday.data_vars["PET"]/10.,
                     TMIN=self._create_dummy_TMIN(day, ds_oneday.data_vars["TEMP"]),
                     TMAX=self._create_dummy_TMAX(day, ds_oneday.data_vars["TEMP"]),
                     IRRAD=self._create_dummy_IRRAD(day, ds_oneday.data_vars["PET"]),
                     DTEMP=ds_oneday.data_vars["TEMP"] + 2.5,
                     RAIN=ds_oneday.data_vars["P"]/10.)

    def __call__(self, day, row, col):
        day = check_date(day)
        if day != self.active_day:
            self._read_new_layer(day)
            self.active_day = day

        meteo_vars = {"LAT": self.latitude[row], "LON": self.longitude[col], "DAY": day}
        for varname, meteo_variable in self.active_layers.items():
            meteo_vars[varname] = float(meteo_variable[row, col].values)
        return self.weather_data_container(**meteo_vars)

    def _create_dummy_TMIN(self, day, TEMP):
        return TEMP - 5.

    def _create_dummy_TMAX(self, day, TEMP):
        return TEMP + 5.

    def _create_dummy_IRRAD(self, day, ET0):
        return ET0 * 2.45E6  # Derive directly from ET0 * latent heat for vaporization
