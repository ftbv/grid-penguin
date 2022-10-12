from ..models import Edge
from ..models import GridObject

import numpy as np

BARG_TO_PASCAL = 100000
mass_flows = [
    629000,
    605800,
    583000,
    560700,
    539200,
    518700,
    499500,
    481600,
    465200,
    450500,
    437600,
    426500,
    417300,
    410100,
    404800,
    401600,
    400300,
    401000,
    403600,
    408100,
    414500,
    422500,
    432300,
    443600,
    456400,
    470500,
    485900,
    502300,
    519700,
    538000,
    556900,
    576400,
    596200,
    616300,
    636400,
    656500,
    676300,
    695700,
    714600,
    732800,
    750100,
    766500,
    781800,
    795800,
    808500,
    819600,
    829300,
    837200,
    843400,
    847700,
    850200,
    850700,
    849300,
    845800,
    840400,
    833000,
    823600,
    812400,
    799300,
    784500,
    768000,
    750100,
    730800,
    710400,
    689000,
    666800,
    644200,
    621400,
    598500,
    575500,
    552400,
    529000,
    505500,
    481700,
    457900,
    434000,
    410100,
    386400,
    362800,
    339500,
    316700,
    294400,
    272800,
    251900,
    232000,
    213000,
    195200,
    178700,
    163500,
    149800,
    137500,
    126900,
    118000,
    110800,
    105400,
    101800,
    100000,
    100100,
    102000,
    105700,
]

mass_flows = np.array(mass_flows)
mass_flows = np.append(np.ones(100) * 629000, mass_flows[:-1])
mass_flows = np.append(mass_flows, np.ones(100) * 102000)
TIME_STEPS = len(mass_flows)
# mass_flows = np.ones(TIME_STEPS)*200000
# # mass_flows2 = (np.arange(9)[::-1]+1)*20000
# mass_flows[:50] = 200000
# # mass_flows[50:(50+len(mass_flows2))] = mass_flows2
# print(mass_flows)
mass_flows /= 3600

temp = np.ones(TIME_STEPS) * 120
# temp[:50] = 120


class Pseudo_Node(GridObject):
    def __init__(self, temp):
        self.temp = temp
        self.pressure = np.full((2, TIME_STEPS), np.nan, dtype=float)

    def get_outlet_temp(self, pholder):

        return self.temp[GridObject._current_step]


class Signle_Edge_System:
    def __init__(self, mass_flows, temp, ground_temp, pipe_len, u, d):
        interval_length = 900

        self.node1 = Pseudo_Node(temp)
        self.node2 = Pseudo_Node(temp)
        self.node1.pressure = np.full((2, TIME_STEPS), 3 * BARG_TO_PASCAL, dtype=float)

        self.edge = Edge(
            blocks=TIME_STEPS,
            historical_t_in=temp[0],
            diameter=d,
            length=pipe_len,
            thermal_resistance=1 / u / np.pi / d,  # Valkema p25
            t_ground=ground_temp,
            max_flow_speed=3,
            min_flow_speed=0,
            friction_coefficient=8.054,
        )
        # 0.00248578125000009
        self.edge.link(
            nodes=(
                (self.node1, 0),
                (self.node2, 0),
            )
        )
        self.edge.add_to_grid(
            self.solvable,
            interval_length,
        )

        self.edge.clear()
        GridObject.reset_step()

        self.mass_flows = mass_flows
        self.out_temps = []

    def solvable(self, *args):
        pass

    def solve(self):

        for _ in range(TIME_STEPS):
            time_step = GridObject._current_step
            self.edge.set_mass_flow(0, self.mass_flows[GridObject._current_step])

            GridObject.increase_step()

        return self.edge.temp[1]


if __name__ == "__main__":
    # mass_flow = np.random.randint(2,20, size=15)*10000
    # temp = np.random.randint(70,120, size=15)
    # ground_temp = np.random.randint(0,20,size=15)
    # pipe_len = np.random.randint(1,20,size=15)*1000
    # heat_trans_coef = np.random.randint(1,50, size=15)/10
    # pipe_diameter = np.random.randint(30,80, size=15)/100

    # for m,t,te,l,u,d in zip(mass_flow,temp,ground_temp,pipe_len,heat_trans_coef,pipe_diameter):

    SES = Signle_Edge_System(mass_flows, temp, 10, 5000, 2, 0.5958)
    temp = SES.solve()
    # print(m,t,te,l,u,d)
    print(temp[-200:])
