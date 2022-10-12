import numpy as np  # type: ignore
from simulator.models import Grid, Producer, Branch, Transfer, Junction, Consumer, Edge, Node  # type: ignore

# import cProfile

# blocks = 60  # 10 hours
hts_count = 4
consumers_per_hts = 200
# hts_count = 1
# consumers_per_hts = 1

# consumer is a secondary grid, with about 250 households
consumer_demand = np.array(
    [
        1200 * 10 ** 3,
        1200 * 10 ** 3,
        1200 * 10 ** 3,
        1200 * 10 ** 3,
        1200 * 10 ** 3,
        600 * 10 ** 3,
        600 * 10 ** 3,
        600 * 10 ** 3,
        600 * 10 ** 3,
        600 * 10 ** 3,
    ]
)
blocks = consumer_demand.shape[0]

primary_grid_mass_flow = 600
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

last_supply_node: Node = producer
last_supply_node_slot: int = 0
last_return_node: Node = producer
last_return_node_slot: int = 1

for i in range(0, hts_count):
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

    transfer = Transfer(
        blocks=blocks,
        surface_area=400,  # in m^2
        heat_transfer_q=0.8,  # See Palsson 1999 p45
        # Valkema p21/22 and U = k / (m_1 ^ -q + m_2 ^ -q)
        heat_transfer_k=5 * 10 ** 6 / 400 * (400 ** (-0.8) + 400 ** (-0.8)),
    )

    grid.add_node(transfer)

    if i < hts_count - 1:
        supply_blank_edge = Edge(
            blocks=blocks,
            historical_t_in=90,
            diameter=0.5958,
            length=100,
            thermal_resistance=1.36,  # Valkema p25
        )
        grid.add_edge(supply_blank_edge)

        return_blank_edge = Edge(
            blocks=blocks,
            historical_t_in=50,
            diameter=0.5958,
            length=100,
            thermal_resistance=1.36,  # Valkema p25
        )
        grid.add_edge(return_blank_edge)

        branch = Branch(blocks=blocks)
        grid.add_node(branch)

        junction = Junction(blocks=blocks)
        grid.add_node(junction)

        supply_edge.link(
            nodes=(
                (last_supply_node, last_supply_node_slot),
                (branch, 0),
            )
        )

        return_edge.link(
            nodes=(
                (junction, 2),
                (last_return_node, last_return_node_slot),
            )
        )

        supply_blank_edge.link(nodes=((branch, 1), (transfer, 0)))
        return_blank_edge.link(nodes=((transfer, 1), (junction, 0)))

        last_supply_node = branch
        last_supply_node_slot = 2
        last_return_node = junction
        last_return_node_slot = 1
    else:
        supply_edge.link(
            nodes=(
                (last_supply_node, last_supply_node_slot),
                (transfer, 0),
            )
        )

        return_edge.link(
            nodes=(
                (transfer, 1),
                (last_return_node, last_return_node_slot),
            )
        )

    c_last_supply_node: Node = transfer
    c_last_supply_node_slot: int = 2
    c_last_return_node: Node = transfer
    c_last_return_node_slot: int = 3

    for j in range(0, consumers_per_hts):
        c_supply_edge = Edge(
            blocks=blocks,
            historical_t_in=85,
            diameter=0.203,
            length=2000,
            thermal_resistance=1.9,  # Valkema p25
        )
        grid.add_edge(c_supply_edge)

        c_return_edge = Edge(
            blocks=blocks,
            historical_t_in=46,
            diameter=0.203,
            length=2000,
            thermal_resistance=1.9,  # Valkema p25
        )
        grid.add_edge(c_return_edge)

        consumer = Consumer(
            demand=consumer_demand.copy(),
            surface_area=400,  # in m^2
            heat_transfer_q=0.8,  # See Palsson 1999 p45
            # Valkema p21/22
            heat_transfer_k=5 * 10 ** 6 / 400 * (400 ** (-0.8) + 400 ** (-0.8)),
        )
        grid.add_node(consumer)

        if j < consumers_per_hts - 1:
            c_supply_blank_edge = Edge(
                blocks=blocks,
                historical_t_in=85,
                diameter=0.203,
                length=100,
                thermal_resistance=1.9,  # Valkema p25
            )
            grid.add_edge(c_supply_blank_edge)

            c_return_blank_edge = Edge(
                blocks=blocks,
                historical_t_in=46,
                diameter=0.203,
                length=100,
                thermal_resistance=1.9,  # Valkema p25
            )
            grid.add_edge(c_return_blank_edge)

            c_branch = Branch(blocks=blocks)
            grid.add_node(c_branch)

            c_junction = Junction(blocks=blocks)
            grid.add_node(c_junction)

            c_supply_edge.link(
                nodes=(
                    (c_last_supply_node, c_last_supply_node_slot),
                    (c_branch, 0),
                )
            )

            c_return_edge.link(
                nodes=(
                    (c_junction, 2),
                    (c_last_return_node, c_last_return_node_slot),
                )
            )

            c_supply_blank_edge.link(nodes=((c_branch, 1), (consumer, 0)))
            c_return_blank_edge.link(nodes=((consumer, 1), (c_junction, 0)))

            c_last_supply_node = c_branch
            c_last_supply_node_slot = 2
            c_last_return_node = c_junction
            c_last_return_node_slot = 1
        else:
            c_supply_edge.link(
                nodes=(
                    (c_last_supply_node, c_last_supply_node_slot),
                    (consumer, 0),
                )
            )

            c_return_edge.link(
                nodes=(
                    (consumer, 1),
                    (c_last_return_node, c_last_return_node_slot),
                )
            )


grid.link_nodes(True)
producer.opt_temp = np.full(blocks, 90, dtype=float)
