import pywanda
import os
import numpy as np


class Wanda_Model(object):
    def __init__(self, time_intv, time_step):
        wandafile_dir = r"C:\Users\84186\Documents\Wanda"
        wandacase_fullpath = os.path.join(wandafile_dir, "experiment_py.wdi")
        wandabin_directory = r"c:\Program Files (x86)\Deltares\Wanda 4.6\Bin\\"

        model = pywanda.WandaModel(wandacase_fullpath, wandabin_directory)

        model.get_property("Simulation time").set_scalar(time_step * time_intv)
        model.get_property("Time step").set_scalar(time_intv)

        bound1 = model.get_component("BOUNDMT B3")
        ms_table1 = bound1.get_property("Action table").get_table()

        bound2 = model.get_component("BOUNDMT B4")
        bound2.get_property("Mass flow at t = 0 [s]").set_scalar(-20)
        ms_table2 = bound2.get_property("Action table").get_table()

        pipe = model.get_component("PIPE P2")
        pipe.get_property("Heat transf coef").set_scalar(1)
        pipe.get_property("Advection velocity").set_scalar(0.501)
        node = model.get_node("NODE C")

        self.model = model
        self.pipe = pipe
        self.node_out = node
        self.ms_table1 = ms_table1
        self.ms_table2 = ms_table2
        self.bound1 = bound1
        self.bound2 = bound2

        # model.save_model_input()
        # model.run_unsteady()

        # print(node.get_property("Temperature").get_series())
        # print(pipe.get_property("Temperature 1").get_series())

    def set_ms(self, mass_flow_time_table):
        self.ms_table1.set_float_data(mass_flow_time_table)
        self.bound1.get_property("Mass flow at t = 0 [s]").set_scalar(
            mass_flow_time_table[1, 0]
        )
        mass_flow_time_table[1] = -mass_flow_time_table[1]
        self.ms_table2.set_float_data(mass_flow_time_table)
        self.bound2.get_property("Mass flow at t = 0 [s]").set_scalar(
            mass_flow_time_table[1, 0]
        )

        self.model.run_unsteady()

        return self.node_out.get_property("Temperature").get_series()


def build_model():

    wandafile_dir = r"C:\Users\84186\Documents\Wanda"
    wandacase_fullpath = os.path.join(wandafile_dir, "experiment_py.wdi")
    wandabin_directory = r"c:\Program Files (x86)\Deltares\Wanda 4.6\Bin\\"

    model = pywanda.WandaModel(wandacase_fullpath, wandabin_directory)

    model.get_property("Simulation time").set_scalar(3600 * 24)
    model.get_property("Time step").set_scalar(90)

    posx = 10
    posy = -10
    loc = [posx, posy]
    bound1 = model.add_component("Heat boundMT", loc)
    bound1.get_property("Temperature").set_scalar("constant")
    bound1.get_property("Constant temperature").set_scalar(120)
    bound1.get_property("Mass flow at t = 0 [s]").set_scalar(20)
    bound1.set_use_action_table(True)
    ms_table = bound1.get_property("Action table").get_table()
    ms_table.set_float_data([[0, 3600 * 24], [20, 40]])

    loc[0] += 5
    pipe = model.add_component("Heat pipe", loc)
    pipe.get_property("Inner diameter").set_scalar(0.5958)
    pipe.get_property("Length").set_scalar(5000.0)
    pipe.get_property("Wall roughness").set_scalar(0.001)
    pipe.get_property("Heat transf coef").set_scalar(2)
    pipe.get_property("Advection velocity").set_scalar(1)

    loc[0] -= 2
    node1 = model.add_node("Heat node init p", loc)
    node1.get_property("Elevation").set_scalar(0.0)
    node1.get_property("Pressure at t = 0 [s]").set_scalar(100000)
    model.connect(bound1, 1, node1)
    model.connect(pipe, 1, node1)

    loc[0] += 2 + 5
    bound2 = model.add_component("Heat boundMT", loc)
    bound2.get_property("Temperature").set_scalar("constant")
    bound2.get_property("Constant temperature").set_scalar(120)
    bound2.get_property("Mass flow at t = 0 [s]").set_scalar(-20)
    bound2.set_use_action_table(True)
    ms_table = bound2.get_property("Action table").get_table()
    ms_table.set_float_data([[0, 3600 * 24], [-20, -40]])
    node2 = model.connect(pipe, 2, bound2, 1)
    node2.get_property("Elevation").set_scalar(0.0)

    model.save_model_input()
    model.run_steady()


if __name__ == "__main__":
    wanda_model = Wanda_Model()
    ms = np.array([[0, 86400], [20, 40]])
    print(wanda_model.set_ms(ms))
    # model.reload_output()
    # pipe1 = model.get_component('PIPE P2')
    # pressure = pipe1.get_property('Pressure 2')
    # a = pressure.get_series()
    # print(a)
