import numpy as np  # type: ignore
from grid.models import Grid, Producer, Consumer, Edge  # type: ignore

# import cProfile

# consumer is a secondary grid, with about 250 households
consumer_demand = np.array(
    [
        1200 * 10 ** 5,
        1200 * 10 ** 5,
        1200 * 10 ** 5,
        1200 * 10 ** 5,
        1200 * 10 ** 5,
        600 * 10 ** 5,
        600 * 10 ** 5,
        600 * 10 ** 5,
        600 * 10 ** 5,
        600 * 10 ** 5,
    ]
)
blocks = consumer_demand.shape[0]

secondary_grid_mass_flow = 60

"""
max mass flow for DN200:
* area approx 0.03 m2
* velocity max 2.0 m/s
* 963kg/m^3
=> 62.2 kg/s

max mass flow for DN600 = 800 kg/s (Valkema p24)
"""

grid = Grid(
    interval_length=60 * 10,  # 10 min
)

producer = Producer(blocks=blocks)
grid.add_node(producer)


supply_edge = Edge(
    blocks=blocks,
    historical_t_in=90,
    diameter=0.5958,
    length=2704,
    thermal_resistance=1.36,  # Valkema p25
)
grid.add_edge(supply_edge)

return_edge = Edge(
    blocks=blocks,
    historical_t_in=50,
    diameter=0.5958,
    length=2704,
    thermal_resistance=1.36,  # Valkema p25
)
grid.add_edge(return_edge)


consumer = Consumer(
    demand=consumer_demand.copy(),
    surface_area=400,  # in m^2
    heat_transfer_q=0.8,  # See Palsson 1999 p45
    # Valkema p21/22
    # Jichen: This caculation does not make sense
    heat_transfer_k=5 * 10 ** 6 / 400 * (400 ** (-0.8) + 400 ** (-0.8)),
    max_mass_flow_p=2000,
)
grid.add_node(consumer)


supply_edge.link(
    nodes=(
        (producer, 0),
        (consumer, 0),
    )
)

return_edge.link(
    nodes=(
        (consumer, 1),
        (producer, 1),
    )
)


grid.link_nodes(False)

producer.opt_temp = np.full(blocks, 90, dtype=float)
