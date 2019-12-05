from pathlib import Path
import time
import datetime as dt

import numpy as np
import pandas as pd
import xarray as xr

from griddedwofostbmi.model import GriddedWOFOSTBMI


if __name__ == "__main__":
    root = Path.cwd().parent
    conf_file = root / "config" / "gridded_wofost.yaml"
    g = GriddedWOFOSTBMI(conf_file)
    template_array = np.ndarray(shape=(314, 292), dtype=np.float64)
    template_array[:, :] = np.NaN

    # Create output DataSet
    meteo_ds = xr.open_dataset(g.config.weather_variables.location)
    days = pd.date_range(g.config.runtime.start_date, g.config.runtime.end_date)
    ds = xr.Dataset({"LAI": xr.DataArray(data=np.full((len(days), 314, 292),
                                                      dtype=np.float64,
                                                      fill_value=np.NaN),
                                         dims=("time", "lat", "lon"),
                                         coords={"time": days,
                                                 "lat": meteo_ds.lat,
                                                 "lon": meteo_ds.lon})
                     })

    # Get initial values
    day = g.get_current_time()
    dest_array = np.copy(template_array)
    g.get_value("LAI", dest_array)
    ds.LAI.loc[dict(time=day)] = dest_array

    # Run model over entire time-series writing
    while day != dt.date(2012, 12, 31):
        t1 = time.time()
        g.update()
        day += dt.timedelta(days=1)
        print(f"Time step {day} took {time.time()-t1} seconds.")

        dest_array = np.copy(template_array)
        g.get_value("LAI", dest_array)
        ds.LAI.loc[dict(time=day)] = dest_array

    ds.to_netcdf("wofostgridded_LAI.nc")
