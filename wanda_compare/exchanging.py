import numpy as np
import matplotlib.pyplot as plt
from perlin_noise import PerlinNoise
import pywanda
import os

from ..models.heat_exchanger import solve

t_supply_p = 110  # in degrees C
t_supply_s = 70  # in degrees C
t_return_s = 45  # in degrees C
max_ms_p = 2000
ms_s = 500
heat_capacity = 4181.3  # in J/kg/K
surface_area = 10  # in m^2
q_coef = 0.8  # See Palsson 1999 p45
k = 5000  # See Palsson 1999 p51 or Valkema p21/22


def calculate_u(k, q, max_ms_p, ms_s, surface_area):

    u = (k / (max_ms_p ** (-q) + ms_s ** (-q))) * surface_area

    return u


def solve_ms_with_u(k, q, A, u):
    return (k * A / (2 * u)) ** (-1 / q)


class Wanda_Model(object):
    def __init__(self):
        wandafile_dir = r"C:\Users\84186\Documents\Wanda"
        wandacase_fullpath = os.path.join(wandafile_dir, "single_hx.wdi")
        wandabin_directory = r"c:\Program Files (x86)\Deltares\Wanda 4.6\Bin\\"

        self.model = pywanda.WandaModel(wandacase_fullpath, wandabin_directory)

        # model.get_property("Simulation time").set_scalar(time_step*time_intv)
        # model.get_property("Time step").set_scalar(time_intv)

        self.bound1 = self.model.get_component("BOUNDMT B1")

        bound1 = model.get_component("BOUNDMT B1")
        # ms_table1 = bound1.get_property("Action table").get_table()

        self.bound2 = self.model.get_component("BOUNDMT B2")
        # bound2.get_property("Mass flow at t = 0 [s]").set_scalar(-20)
        # ms_table2 = bound2.get_property("Action table").get_table()

        self.bound3 = self.model.get_component("BOUNDMT B4")
        self.bound4 = self.model.get_component("BOUNDMT B3")

        self.hx = self.model.get_component("HEX4WAY H1")
        self.node1 = self.model.get_node("NODE A")
        self.node2 = self.model.get_node("NODE B")
        self.node3 = self.model.get_node("NODE C")
        self.node4 = self.model.get_node("NODE D")

        # self.model.reload_output()

        # model.save_model_input()
        # model.run_steady()

        # print(node.get_property("Temperature").get_series())
        # print(pipe.get_property("Temperature 1").get_series())

    def run(self, u, temp_p, temp_s, ms_p, ms_s):
        self.bound1.get_property("Mass flow at t = 0 [s]").set_scalar(ms_p)
        self.bound1.get_property("Constant temperature").set_scalar(temp_p)
        self.bound2.get_property("Mass flow at t = 0 [s]").set_scalar(-ms_p)

        self.bound3.get_property("Mass flow at t = 0 [s]").set_scalar(ms_s)
        self.bound3.get_property("Constant temperature").set_scalar(temp_s)
        self.bound4.get_property("Mass flow at t = 0 [s]").set_scalar(-ms_s)

        self.hx.get_property("Heat transfer coefficient").set_scalar(u)

        self.model.run_steady()

        temp_ret_p = self.node2.get_property("Temperature").get_scalar_float()
        temp_ret_s = self.node4.get_property("Temperature").get_scalar_float()

        return temp_ret_p, temp_ret_s


def print_out_temp_with_same_u():
    for _ in range(10):
        ms_s = np.random.randint(100, 2000)

        (mass_flow_p, t_return_p, t_supply_s, q) = solve(
            t_supply_p,
            t_supply_s,
            t_return_s,
            max_ms_p,
            ms_s,
            heat_capacity,
            surface_area,
            q_coef,
            k,
        )

        u = calculate_u(k, q_coef, mass_flow_p, ms_s, surface_area)
        print(u)

        wanda_model = Wanda_Model()
        wanda_ret_p, wanda_sup_s = wanda_model.run(
            u, t_supply_p, t_return_s, mass_flow_p, ms_s
        )

        print(t_return_p, wanda_ret_p, t_supply_s, wanda_sup_s)


def plot_u_with_ms():
    ms_s = np.arange(1, 11) * 200
    ms_p = np.arange(1, 11) * 200
    ms_s, ms_p = np.meshgrid(ms_s, ms_p)
    u = calculate_u(k, q_coef, ms_p, ms_s, surface_area)
    avg_u = np.mean(u)
    avg_ms = solve_ms_with_u(k, q_coef, surface_area, avg_u)
    print(avg_ms, avg_u)
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    fig = plt.figure()
    ax = fig.add_subplot(111, projection="3d")
    ax.plot_surface(ms_s, ms_p, u)
    ax.scatter([[avg_ms]], [[avg_ms]], [[avg_u]], c="r")

    ax.invert_yaxis()
    ax.set_xlabel("mass flow secondary")
    ax.set_ylabel("mass flow primary")
    ax.set_zlabel("U (W/K)")
    ax.set_title("Heat transfer coefficient (U) with mass flow changes")

    plt.show()


def plot_heat_lines():
    arr_ms_s = np.sort(np.random.randn(100) * 500 + 800)
    arr_ms_s[arr_ms_s < 50] = 50
    arr_ms_p, arr_t_return_p_sim, arr_t_supply_s_sim = [], [], []
    heat_sim = []

    for ms_s in arr_ms_s:
        (mass_flow_p, t_return_p, t_supply_s_real, q) = solve(
            t_supply_p,
            t_supply_s,
            t_return_s,
            max_ms_p,
            ms_s,
            heat_capacity,
            surface_area,
            q_coef,
            k,
        )
        arr_ms_p.append(mass_flow_p)
        arr_t_return_p_sim.append(t_return_p)
        arr_t_supply_s_sim.append(t_supply_s)
        heat_sim.append(mass_flow_p * (t_supply_p - t_return_p) * heat_capacity)

    # calculates different U for wanda
    u_min = calculate_u(k, q_coef, arr_ms_p[0], arr_ms_s[0], surface_area)
    u_max = calculate_u(k, q_coef, arr_ms_p[-1], arr_ms_s[-1], surface_area)
    ms_s_mean = np.mean(arr_ms_s)
    ms_s_mean_idx = np.argmin(np.abs(arr_ms_s - ms_s_mean))
    ms_s_mean = arr_ms_s[ms_s_mean_idx]
    ms_p_mean = arr_ms_p[ms_s_mean_idx]
    u_mean = calculate_u(k, q_coef, ms_p_mean, ms_s_mean, surface_area)
    ms_s_center = (arr_ms_s[-1] - arr_ms_s[0]) * 0.4 + arr_ms_s[0]
    ms_s_center_idx = np.argmin(np.abs(arr_ms_s - ms_s_center))
    ms_s_center = arr_ms_s[ms_s_center_idx]
    ms_p_center = arr_ms_p[ms_s_center_idx]
    u_center = calculate_u(k, q_coef, ms_p_center, ms_s_center, surface_area)

    matrix_wanda_ret_p, matrix_wanda_ret_s = [], []
    matrix_wanda_heat = []
    for u in [u_min, u_max, u_mean, u_center]:
        arr_wanda_ret_p, arr_wanda_ret_s = [], []
        arr_wanda_heat = []
        for ms_s, ms_p in zip(arr_ms_s, arr_ms_p):
            print(ms_s)
            wanda_model = Wanda_Model()
            wanda_ret_p, wanda_sup_s = wanda_model.run(
                u, t_supply_p, t_return_s, ms_p, ms_s
            )
            arr_wanda_ret_p.append(wanda_ret_p)
            arr_wanda_ret_s.append(wanda_sup_s)
            arr_wanda_heat.append(ms_p * (t_supply_p - wanda_ret_p) * heat_capacity)

        matrix_wanda_ret_p.append(arr_wanda_ret_p)
        matrix_wanda_ret_s.append(arr_wanda_ret_s)
        matrix_wanda_heat.append(arr_wanda_heat)

    # plot
    import matplotlib.pyplot as plt

    plt.plot(arr_ms_s, heat_sim, label="simulator")
    plt.plot(arr_ms_s, matrix_wanda_heat[0], label="Wanda U min")
    plt.plot(arr_ms_s, matrix_wanda_heat[1], label="Wanda U max")
    plt.plot(arr_ms_s, matrix_wanda_heat[2], label="Wanda U mean")
    plt.plot(arr_ms_s, matrix_wanda_heat[3], label="Wanda U center")
    plt.legend()
    plt.xlabel("mass flow")
    plt.ylabel("heat exchanged")
    plt.show()

    # calculate error
    mse_min = np.mean((np.array(matrix_wanda_heat[0]) - heat_sim) ** 2) / (10 ** 13)
    mse_max = np.mean((np.array(matrix_wanda_heat[1]) - heat_sim) ** 2) / (10 ** 13)
    mse_mean = np.mean((np.array(matrix_wanda_heat[2]) - heat_sim) ** 2) / (10 ** 13)
    mse_center = np.mean((np.array(matrix_wanda_heat[3]) - heat_sim) ** 2) / (10 ** 13)
    print("absolute error", mse_min, mse_max, mse_mean, mse_center)

    mse_min = np.mean(((np.array(matrix_wanda_heat[0]) - heat_sim) / heat_sim) ** 2)
    mse_max = np.mean(((np.array(matrix_wanda_heat[1]) - heat_sim) / heat_sim) ** 2)
    mse_mean = np.mean(((np.array(matrix_wanda_heat[2]) - heat_sim) / heat_sim) ** 2)
    mse_center = np.mean(((np.array(matrix_wanda_heat[3]) - heat_sim) / heat_sim) ** 2)
    print("relative error", mse_min, mse_max, mse_mean, mse_center)


if __name__ == "__main__":
    plot_heat_lines()
