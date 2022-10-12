import numpy as np
from os.path import exists, dirname
from collections import defaultdict
from .heat_exchanger import HeatExchanger

absolute_path = dirname(__file__)
path_model = absolute_path + "/interpolated_values/{}"


def generate_values(setpoint_t_supply_s: float, t_return_s: float,
                    hx: HeatExchanger, file_name: str,
                    temp_range: list[float], mass_range: list[float]) -> dict[float, dict[float, float]]:
    """
    Returns a dictionary of interpolation values from a file with specified file_name.
    If the file does not exist, then a file with the given file_name is created and
    values are generated within the given temp_range and mass_range.
    The values are then read from the file and added to a dict
    """
    file_path = path_model.format(file_name)

    if not exists(file_path):
        run_heat_exchanger(setpoint_t_supply_s, t_return_s, hx,
                           temp_range, mass_range, file_name)

    return load_values(file_path)


def load_values(file_path: str) -> dict[float, dict[float, float]]:
    """
    Reads the stored interpolation values from a file, located in file_path.
    Loads the values in a dictionary. The keys represent the t_supply_p values.
    The values inside the main dict are also dictionaries. The keys of the nested
    dict are mass_flow_s values and the corresponding value is the t_return_p values,
    which the HeatExchanger returned, having the t_supply_p and mass_flow_s keys as
    input parameters of the solve method.
    """
    values = defaultdict(dict)
    with open(file_path, "r") as file:
        lines = file.read().splitlines()
        for line in lines:
            value_array = line.split(" ")
            values[float(value_array[0])][float(value_array[1])] = float(value_array[2])

    return values


def run_heat_exchanger(setpoint_t_supply_s: float, t_return_s: float, hx: HeatExchanger,
                       temp_range: list[float], mass_range: list[float], file_name: str):
    """
    Runs the solve method of the input HeatExchanger with values for
    t_supply_p and mass_flow_s within the input ranges.
    The t_supply_p, mass_flow_s and the returned t_return_p values are stored in a file,
    specified by the file_name input.
    """
    file_path = path_model.format(file_name)

    for t in np.arange(temp_range[0], temp_range[1] + 0.015625, 0.015625):
        for m in np.arange(mass_range[0], mass_range[1] + 0.015625, 0.015625):
            mass_flow_p, t_return_p, t_supply_s, q = hx.solve(t, setpoint_t_supply_s, t_return_s, m)
            with open(file_path, "a") as file:
                file.write("%s %s %s\n" % (t, m, t_return_p))
