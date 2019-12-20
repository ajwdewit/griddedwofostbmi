# -*- coding: utf-8 -*-
# Copyright (c) 2019 Wageningeni Environmental Research, Wageningen-UR
# Allard de Wit (allard.dewit@wur.nl), December 2019

from pathlib import Path
import time
import os
import datetime as dt
import gc
import numpy as np
import pandas as pd
import xarray as xr

import psutil

from griddedwofostbmi.model import GriddedWOFOSTBMI


def store_variable_netcdf(day, variable, ref_ds, flip_output=False):
    nrows, ncols = variable.shape
    variable.shape = (1, nrows, ncols)
    latitude = ref_ds.lat[::-1] if flip_output else np.array(ref_ds.lat)
    longitude = np.array(ref_ds.lon)
    ds = xr.Dataset({"LAI": xr.DataArray(data=variable,
                                         dims=("time", "lat", "lon"),
                                         coords={"time": pd.to_datetime([day]),
                                                 "lat": latitude,
                                                 "lon": longitude})
                     })
    fname = Path(os.getcwd()) / "netcdf" / f"mosselle_LAI_{day}.nc"
    ds.to_netcdf(fname)


if __name__ == "__main__":
    process = psutil.Process(os.getpid())
    root = Path.cwd().parent
    conf_file = root / "config" / "gridded_wofost.yaml"

    # Started gridded WOFOST
    g = GriddedWOFOSTBMI(conf_file)

    # input arrays for Transpiration and PotTrans
    template_array = np.full(shape=(314, 292), dtype=np.float64, fill_value=np.NaN)
    transpiration = np.ones_like(template_array)
    pottrans = np.ones_like(template_array)

    # Template dataset
    meteo_ds = xr.open_dataset(g.config.weather_variables.location)

    # Get initial values
    day = g.get_current_time()
    output_array = g.get_value("LAI")
    store_variable_netcdf(day, output_array, meteo_ds, flip_output=g.config.model_output.flip_output_array)

    # Run model over entire time-series writing daily output to netcdf
    while day != dt.date(2012, 12, 31):
        t1 = time.time()
        # Externally set the values for Transpiration and PotTrans
        g.set_value("Transpiration", transpiration)
        g.set_value("PotTrans", pottrans)
        g.update()
        day = g.get_current_time()

        output_array = g.get_value("LAI")
        store_variable_netcdf(day, output_array, meteo_ds, flip_output=g.config.model_output.flip_output_array)
        gc.collect()

        # Get memory info of current process
        m = process.memory_info()
        print(f"Time step {day} took {time.time()-t1:.1f} seconds, using {m.rss/1048576.:.0f} Mb of memory.")
