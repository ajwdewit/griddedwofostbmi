from pcse.engine import Engine
from pcse.traitlets import Int

class GridAwareEngine(Engine):
    """PCSE engine for running WOFOST on a grid.

    The only difference is that the GridAwareEngine is "aware" of the row/col number
    of the grid and can thus request the proper weather data for the location in the
    grid.
    """
    row = Int
    col = Int

    def __init__(self, row, col, **kwargs):
        self.row = int(row)
        self.col = int(col)
        super().__init__(**kwargs)

    # get driving variables needs to be redefined in order to take row/col into account
    def _get_driving_variables(self, day):
        """Get driving variables, compute derived properties and return it.
        """
        drv = self.weatherdataprovider(day, self.row, self.col)

        # average temperature and average daytemperature (if needed)
        if not hasattr(drv, "TEMP"):
            drv.add_variable("TEMP", (drv.TMIN + drv.TMAX) / 2., "Celcius")
        if not hasattr(drv, "DTEMP"):
            drv.add_variable("DTEMP", (drv.TEMP + drv.TMAX) / 2., "Celcius")

        return drv

    @property
    def start_date(self):
        return self.agromanager.start_date

    @property
    def end_date(self):
        return self.agromanager.end_date
