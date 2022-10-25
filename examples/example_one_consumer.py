# An simplified example to run the simulator without loading dataset and configurations
# to avoid import error, the script has to be run one folder above the root folder (grid-penguin)
# python -m grid-penguin.examples.example_one_consumer

import numpy as np

from ..cases.one_consumer import build_grid
from util import config

if __name__ == "__main__":
    # define heat demand and electricity price here
    heat_demand = np.ones(config.TimeParameters["PlanningHorizon"]) * 30
    electricity_price = np.ones(config.TimeParameters["PlanningHorizon"]) * 25

    # build the grid
    grid = build_grid(
        [heat_demand],
        [electricity_price],
        config,
    )

    # reset the grid with demand. This is a necessary step before running the grid
    # here we use the same heat demand as when we build the grid as it is the first time the grid is run
    grid.reset([heat_demand])

    # run the grid of the whole 24 hours period.
    # we set the producer outlet temperature to always be 90 degree and electricity production to always be 20 MW
    grid.run(
        temp=[np.ones(config.TimeParameters["PlanningHorizon"]) * 90],
        electricity=[np.ones(config.TimeParameters["PlanningHorizon"]) * 20],
    )

    # the id of all 4 objects in the grid. They come the same order as they are created in build_grid()
    producer_id = 0
    consumer_id = 1
    supply_edge_id = 2
    return_edge_id = 3

    """
    Get the id of objects creating the grid depending on their name.
    """
    obj_id_name = grid.get_id_name_all_obj()
    producer_id = [k for k, v in obj_id_name.items() if v == "CHP"][0]
    consumer_id = [k for k, v in obj_id_name.items() if v == "Consumer"][0]
    sup_edge_id = [k for k, v in obj_id_name.items() if v == "Edge"][0]
    ret_edge_id = [k for k, v in obj_id_name.items() if v == "Edge"][1]

    # get full basic status of the grid
    grid_status = grid.get_object_status(
        object_ids=[producer_id, consumer_id, sup_edge_id, ret_edge_id],
        get_temp=True,
        get_ms=True,
        get_pressure=False,
        get_violation=False,
    )

    # grid_status[0]; producer status, grid_status[0][0]: first status of producer: temperature
    # grid_status[0][0][0]: first row of temperature: outlet temp
    producer_return_temp = grid_status[0]["Temp"][0]
    print("producer return temp: ", producer_return_temp)

    consumer_return_mass_flow = grid_status[1]
    print("consumer return mass flow: ", consumer_return_mass_flow)

    # you can also get the object status direct from the object, skipping the grid interface
    for consumer in grid.consumers:
        consumer_return_mass_flow = consumer.mass_flow[1]
        print(
            "consumer return mass flow got from a different way: ",
            consumer_return_mass_flow,
        )

