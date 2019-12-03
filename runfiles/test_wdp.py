from  griddedwofostbmi.dataproviders import WFLOWWeatherDataProvider

from dotmap import DotMap
import yaml

config = DotMap(yaml.safe_load(open(r"C:\data\UserData\sources\griddedwofostbmi\config\gridded_wofost.yaml")))

wdp = WFLOWWeatherDataProvider(config)
r = wdp("2010-01-01", row=100, col=120)
print(r)
print(1)


