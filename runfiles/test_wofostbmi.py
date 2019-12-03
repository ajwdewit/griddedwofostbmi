from pathlib import Path
import numpy as np

from griddedwofostbmi.model import GriddedWOFOSTBMI


if __name__ == "__main__":
    root = Path.cwd().parent
    conf_file = root / "config" / "gridded_wofost.yaml"
    g = GriddedWOFOSTBMI(conf_file)
    for i in range(100):
        g.update()
    print(g.get_current_time())
    dest_array = np.ndarray(shape=(314,292), dtype=np.float64)
    dest_array[:,:] = np.NaN
    g.get_value("LAI", dest_array)
    print(1)