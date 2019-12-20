from pcse.base import SimulationObject, RatesTemplate
from pcse.traitlets import Float
from pcse.util import limit
from pcse.decorators import prepare_rates


class WFLOWForcedEvapotranspiration(SimulationObject):
    _TRA = 1.0
    _TRAMX = 1.0

    class RateVariables(RatesTemplate):
        EVSMX = Float(None)
        EVS = Float(None)
        TRAMX = Float(None)
        TRA = Float(None)
        RFTRA = Float(None)

    def initialize(self, day, kiosk, parvalues):
        self.rates = self.RateVariables(kiosk, publish=["TRAMX", "TRA", "RFTRA", "EVSMX", "EVS"])

    @prepare_rates
    def __call__(self, day, drv):
        r = self.rates

        # Soil ET is computed by WFLOW, set it to zero here
        r.EVSMX = 0.
        r.EVS = 0.
        r.TRA = self._TRA
        r.TRAMX = self._TRAMX

        # compute reduction factor for transpiration (RFTRA) directly from
        # Forced WFLOW transpiration and potential transpiration
        try:
            r.RFTRA = limit(0.0, 1.0, r.TRA/r.TRAMX)
        except ZeroDivisionError as e:
            msg = f"Zero Division occurred when computing RFTRA at day {day}"
            self.logger.warn(msg)
            print(msg)
            r.RFTRA = 1.0

        return r.TRA, r.TRAMX

    @prepare_rates
    def _set_variable_TRA(self, value):
        self._TRA = value
        return {"TRA": None}

    @prepare_rates
    def _set_variable_TRAMX(self, value):
        self._TRAMX = value
        return {"TRAMX": None}



