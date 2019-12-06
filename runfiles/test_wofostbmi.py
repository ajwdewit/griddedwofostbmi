# -*- coding: utf-8 -*-
# Copyright (c) 2019 Wageningeni Environmental Research, Wageningen-UR
# Allard de Wit (allard.dewit@wur.nl), December 2019

from pathlib import Path
import time
import os
import datetime as dt
import gc

import psutil
import numpy as np
import pandas as pd
import xarray as xr

from griddedwofostbmi.model import GriddedWOFOSTBMI


def store_variable_netcdf(day, variable, ref_ds):
    nrows, ncols = variable.shape
    variable.shape = (1, nrows, ncols)
    ds = xr.Dataset({"LAI": xr.DataArray(data=variable,
                                         dims=("time", "lat", "lon"),
                                         coords={"time": pd.to_datetime([day]),
                                                 "lat": ref_ds.lat,
                                                 "lon": ref_ds.lon})
                     })
    fname = Path(os.getcwd()) / "netcdf" / f"mosselle_LAI_{day}.nc"
    ds.to_netcdf(fname)


if __name__ == "__main__":
    process = psutil.Process(os.getpid())
    root = Path.cwd().parent
    conf_file = root / "config" / "gridded_wofost.yaml"
    g = GriddedWOFOSTBMI(conf_file)
    template_array = np.full(shape=(314, 292), dtype=np.float64, fill_value=np.NaN)

    # Template dataset
    meteo_ds = xr.open_dataset(g.config.weather_variables.location)

    # Get initial values
    day = g.get_current_time()
    dest_array = np.copy(template_array)
    g.get_value("LAI", dest_array)
    store_variable_netcdf(day, dest_array, meteo_ds)

    # Run model over entire time-series writing daily output to netcdf
    while day != dt.date(2012, 12, 31):
        t1 = time.time()
        g.update()
        day = g.get_current_time()

        dest_array = np.copy(template_array)
        g.get_value("LAI", dest_array)
        store_variable_netcdf(day, dest_array, meteo_ds)
        gc.collect()

        # Get memory info of current process
        m = process.memory_info()
        print(f"Time step {day} took {time.time()-t1:.1f} seconds, using {m.rss/1048576.:.0f} Mb of memory.")
