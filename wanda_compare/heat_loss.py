import numpy as np
import matplotlib.pyplot as plt
from perlin_noise import PerlinNoise

from .pipe1 import Wanda_Model
from .single_edge_system import Single_Edge_System

if __name__ == "__main__":
    time_intv = 15 * 60
    time_step = 4 * 24
    in_temp = 120

    time = np.arange(time_step + 1) * time_intv

    wanda_model = Wanda_Model(time_intv, time_step)
    error_sum = 0
    flow_speed_change_rate_sum = 0
    temp_diff_all = []
    for octv in [2, 10, 100]:
        temp_diff_octv = []
        for i in range(5, 6):
            print(i)
            noise = PerlinNoise(octaves=octv, seed=i)
            noise_val = np.array(
                [noise(i / (time_step + 1)) for i in range(time_step + 1)]
            )
            mass_flow = (noise_val - min(noise_val)) / (
                max(noise_val) - min(noise_val)
            ) * 40 + 10

            out_temp_wanda = wanda_model.set_ms(np.array([time, mass_flow]))
            out_temp_wanda = np.array(out_temp_wanda)
            out_temp_wanda = (out_temp_wanda[1:] + out_temp_wanda[:-1]) / 2

            sim_ms = (mass_flow[1:] + mass_flow[:-1]) / 2
            sim_ms = np.append(np.ones(100) * mass_flow[0], sim_ms)
            temp = np.ones(time_step + 100) * in_temp
            simulator = Single_Edge_System(
                sim_ms, temp, 10, 5000, 1, 0.5958, time_step + 100, time_intv
            )
            out_temp_sim = simulator.solve()[100:]

            flow_speed_change_rate_sum += (
                np.mean(np.abs(np.diff(mass_flow)))
                / 963
                / (0.5958 ** 2 * np.pi)
                / time_intv
            )

            # control group
            mass_flow = np.ones(len(mass_flow)) * np.mean(mass_flow)

            out_temp_wanda_control = wanda_model.set_ms(np.array([time, mass_flow]))
            out_temp_wanda_control = np.array(out_temp_wanda_control)
            out_temp_wanda_control = (
                out_temp_wanda_control[1:] + out_temp_wanda_control[:-1]
            ) / 2

            sim_ms = (mass_flow[1:] + mass_flow[:-1]) / 2
            sim_ms = np.append(np.ones(100) * mass_flow[0], sim_ms)
            temp = np.ones(time_step + 100) * in_temp
            simulator = Single_Edge_System(
                sim_ms, temp, 10, 5000, 1, 0.5958, time_step + 100, time_intv
            )
            out_temp_sim_control = simulator.solve()[100:]

            out_temp_wanda -= out_temp_wanda_control[1] - out_temp_sim_control[1]

            error = np.mean((out_temp_wanda - out_temp_sim) / (120 - out_temp_wanda))
            error_sum += error
            temp_diff_octv.extend(list(out_temp_wanda - out_temp_sim))

        temp_diff_all.append(temp_diff_octv)

    # plt.plot(np.arange(time_step)/4,out_temp_wanda,label='Wanda')
    # plt.plot(np.arange(time_step)/4,out_temp_sim,label='the simulator')
    # plt.xlabel('hour')
    # plt.ylabel('degree celsius')
    # plt.legend()
    # plt.show()

    # print(error_sum/10, flow_speed_change_rate_sum/10)

    plt.hist(
        temp_diff_all,
        20,
        label=["low change rate", "medium change rate", "high change rate"],
    )
    plt.xlabel("temperature difference")
    plt.legend()
    plt.show()
