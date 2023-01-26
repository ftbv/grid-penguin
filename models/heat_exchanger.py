# A class that models a head exchanger

import math
import warnings
from scipy import optimize  # type: ignore
from typing import Tuple
from .timing import Timing

timing = Timing(start=False)
tolerance = 0.001


class HeatExchanger:

    def __init__(
            self,
            heat_capacity: float = 4181.3,  # in J/kg/K
            max_mass_flow_p: float = 300,
            surface_area: float = 10,  # in m^2
            heat_transfer_q: float = 0.8,  # See Palsson 1999 p45
            heat_transfer_k: float = 50000,  # See Palsson 1999 p51
            heat_transfer_k_max: float = None,  # these two variables are for dynamic HX behaviour in VT grid
            demand_capacity: float = None,    # these two variables are for dynamic HX behaviour in VT grid
    ):
        self.heat_capacity = heat_capacity
        self.max_mass_flow_p = max_mass_flow_p
        self.surface_area = surface_area
        self.heat_transfer_q = heat_transfer_q
        self.heat_transfer_k = heat_transfer_k
        self.heat_transfer_k_max = heat_transfer_k_max
        self.demand_capacity = demand_capacity
        self.interpolation = None

    def minimum_t_supply_p(
        self,
        q: float,
        t_supply_s: float,  # in degrees C
        mass_flow_p: float,  # in kg/s
        mass_flow_s: float,  # in kg/s
        demand:float = None, # in MW
    ) -> float:
        """
        Minimum primary supply inlet temperature calculated based on the maximum primary
        and secondary side mass flow and heat demand.
        For the calculation see https://en.wikipedia.org/wiki/Logarithmic_mean_temperature_difference
        """
        k = self.get_k(demand)
        u = k / (
            mass_flow_p ** (-self.heat_transfer_q) + mass_flow_s ** (-self.heat_transfer_q)
        )
        lmtd = q / u / self.surface_area
        dt_p = q / mass_flow_p / self.heat_capacity
        dt_s = q / mass_flow_s / self.heat_capacity
        a = math.exp((dt_p - dt_s) / lmtd)

        return (t_supply_s - a * (dt_p + t_supply_s - dt_s)) / (1 - a)

    def solve(
        self,
        t_supply_p: float,  # in degrees C
        setpoint_t_supply_s: float,  # in degrees C
        t_return_s: float,  # in degrees C
        mass_flow_s: float,  # in kg/s
        demand: float, # in MW
    ) -> Tuple[float, float, float, float]:
        """
        Returns primary mass flow, primary return temperature,
        secondary return temperature and fulfilled demand

        If the valve (on the primary side) if fully open and resulting
        mass flow is not enough to satisfy customer demand, the heat exchanger will
        be in its so-called hydraulic regime and the secondary mass flow and
        return temperature will be affected. See Giraud 2015 (b) p 82

        See also https://en.wikipedia.org/wiki/NTU_method
        """
        timing.start()

        k = self.get_k(demand)
        t_supply_s = min(setpoint_t_supply_s, t_supply_p - 0.1)
        demanded_q = mass_flow_s * self.heat_capacity * (t_supply_s - t_return_s)

        if demanded_q < 1:
            timing.stop()
            return 0, t_supply_p, t_return_s, 0

        c_min = min(self.max_mass_flow_p, mass_flow_s) * self.heat_capacity
        q_max = c_min * (t_supply_p - t_return_s)

        c_max = max(self.max_mass_flow_p, mass_flow_s) * self.heat_capacity
        c_r = c_min / c_max

        u = k / (
            self.max_mass_flow_p ** (-self.heat_transfer_q) + mass_flow_s ** (-self.heat_transfer_q)
        )

        ntu = u * self.surface_area / c_min

        if c_r == 1:
            e = ntu / (1 + ntu)
        elif c_r == 0:
            e = 1 - math.exp(-ntu)
        else:
            e = (1 - math.exp(-ntu * (1 - c_r))) / (1 - c_r * math.exp(-ntu * (1 - c_r)))

        thermal_max_q = e * q_max
        if thermal_max_q < demanded_q:
            q = thermal_max_q
            mass_flow_p = self.max_mass_flow_p
            t_return_p = t_supply_p - q / self.max_mass_flow_p / self.heat_capacity
            t_supply_s = t_return_s + q / mass_flow_s / self.heat_capacity

            return mass_flow_p, t_return_p, t_supply_s, q

        q = demanded_q
        closest_t = math.floor(t_supply_p / 0.015625) * 0.015625
        closest_mass = math.floor(mass_flow_s / 0.015625) * 0.015625

        if self.interpolation is None or \
                closest_t not in self.interpolation or \
                closest_mass not in self.interpolation[closest_t]:

            t_return_p = self._thermal_regime(
                t_in_1=t_supply_p,  # in degrees C
                t_in_2=t_return_s,  # in degrees C
                t_out_2=t_supply_s,  # in degrees C
                q=q,  # in W
                k=k,
            )
        else:
            # perform Bilinear Interpolation
            x2 = closest_t + 0.015625
            y2 = closest_mass + 0.015625
            x1 = closest_t
            y1 = closest_mass
            y = mass_flow_s
            x = t_supply_p

            q11 = self.interpolation[x1][y1]
            q12 = self.interpolation[x1][y2]
            q21 = self.interpolation[x2][y1]
            q22 = self.interpolation[x2][y2]

            t_return_p = (q11 * (x2 - x) * (y2 - y) +
                          q21 * (x - x1) * (y2 - y) +
                          q12 * (x2 - x) * (y - y1) +
                          q22 * (x - x1) * (y - y1)
                          ) / ((x2 - x1) * (y2 - y1))

        lmtd = ((t_supply_p - t_supply_s) - (t_return_p - t_return_s)) / (
            math.log(t_supply_p - t_supply_s) - math.log(t_return_p - t_return_s)
        )

        mass_flow_p = q / (self.heat_capacity * abs(t_supply_p - t_return_p))

        ua = (
            k
            / (mass_flow_p ** (-self.heat_transfer_q) + mass_flow_s ** (-self.heat_transfer_q))
            * self.surface_area
        )

        q_lmtd = ua * lmtd
        q_tolerance = tolerance * (t_supply_p - t_supply_s) * mass_flow_p * self.heat_capacity

        if abs(q_lmtd - q) > q_tolerance:
            print('heat_exchanger_q: {}, heat_exchanger_k: {},'
                  ' t_supply_p: {}, t_supply_s: {}, t_return_s: {}, t_return_p: {},'
                  ' mass_flow_s: {}, max_mass_flow_p : {}, mass_flow_p: {},'
                  ' demanded_q: {}, thermal_max_q: {}, q_lmtd: {}, lmtd: {}, ua: {}'
                  ' tolerance: {}W'
                  ' c_min: {}, q_max: {}, c_max: {}, c_r: {}, ntu: {}, e: {},'
                  ' max_thermal_t_supply_s: {}, max_thermal_t_return_p: {}'
                  .format(self.heat_transfer_q, k,
                          t_supply_p, t_supply_s, t_return_s, t_return_p,
                          mass_flow_s, self.max_mass_flow_p, mass_flow_p,
                          demanded_q, thermal_max_q, q_lmtd, lmtd, ua,
                          q_tolerance,
                          c_min, q_max, c_max, c_r, ntu, e,
                          t_return_s + thermal_max_q / mass_flow_s / self.heat_capacity,
                          t_supply_p - thermal_max_q / self.max_mass_flow_p /
                          self.heat_capacity)
                  )
            warnings.warn('Precision error in heat exchanger: '
                          'probably area or k is too large or flow is too small')

        if mass_flow_p > self.max_mass_flow_p + 0.0001:
            print("{} > {}".format(mass_flow_p, self.max_mass_flow_p))
            raise Exception("Heat exchanger caused mass_flow_p to exceed limit")

        timing.stop()
        return mass_flow_p, t_return_p, t_supply_s, q

    def _thermal_regime(
        self,
        t_in_1: float,  # in degrees C
        t_in_2: float,  # in degrees C
        t_out_2: float,  # in degrees C
        q: float,  # in W
        k: float,  # transfer coefficient
    ) -> float:
        """
        Provides the mass flow and outlet temperature of side 1 of a heat exchanger.
        Uses Newton Raphson and assumes that the heat exchanger is in its
        thermal regime, i.e. that q can indeed be provided

        For Newton Raphson, see Palsson 1999, p46 and p47
        See Giraud 2015 (b) p 83 for stability issues
        """

        c_1 = (k * self.surface_area * abs(t_in_1 - t_out_2)) / (
            self.heat_capacity * abs(t_out_2 - t_in_2)
        ) ** self.heat_transfer_q

        c_2 = abs(t_in_1 - t_out_2) / abs(t_out_2 - t_in_2)

        def g_1(a: float) -> float:
            return a - 1

        def g_2(a: float) -> float:
            return 1 + (1 - c_2 * g_1(a)) ** self.heat_transfer_q

        def g_3(a: float) -> float:
            return math.log(a)

        def f(a: float) -> float:
            if abs(a - 1) < 0.0001:
                return 0.5

            return g_1(a) / (g_2(a) * g_3(a))

        def diff(a: float) -> float:
            return f(a) - q ** (1 - self.heat_transfer_q) / c_1

        def diff_prime(a: float) -> float:
            if abs(a - 1) < 0.0001:
                return 1 / 2 * (1 / 2 + c_2 * self.heat_transfer_q / 2)

            x_1 = (g_3(a) - g_1(a) / a) / (g_1(a) * g_3(a))
            x_2 = (
                c_2 * self.heat_transfer_q * (1 - c_2 * g_1(a)) ** (self.heat_transfer_q - 1)
            ) / g_2(a)
            df = f(a) * (x_1 + x_2)
            d = diff(a)
            new_alpha = a - d / df

            threshold = 1 / c_2 + 1
            target = abs((new_alpha + threshold) % (2 * threshold) - threshold)

            return d / (a - target)

        alpha = optimize.newton(
            func=diff, fprime=diff_prime, x0=0.5 * (1 / c_2 + 1), tol=tolerance, maxiter=100
        )

        t_out_1 = t_in_2 + alpha * (t_in_1 - t_out_2)
        return t_out_1

    def add_interpolation_values(self,  interpolation: dict[float, dict[float, float]]):
        self.interpolation = interpolation

    def get_k(self, demand=None):
        if self.heat_transfer_k_max is None:
            return self.heat_transfer_k
        else:
            assert demand is not None
            return self.heat_transfer_k_max*np.power(demand/self.demand_capacity,0.3)
    

