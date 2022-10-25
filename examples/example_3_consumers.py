# An simplified example to run the simulator without loading dataset and configurations
# to avoid import error, the script has to be run one folder above the root folder (flex-heat)
# python -m flex-heat.command.experiments.simulator.example_3_consumers

import numpy as np

from ..cases.parallel_consumers import build_grid
from util import config

if __name__ == "__main__":
    # define heat demand and electricity price here
    heat_demand = np.ones(config.TimeParameters["PlanningHorizon"]) * 30
    electricity_price = np.ones(config.TimeParameters["PlanningHorizon"]) * 25
    heat_demands = [heat_demand / 3.1, heat_demand / 3, heat_demand / 2.9]
    # build the grid
    grid = build_grid(
        heat_demands,
        [electricity_price],
        config,
    )

    # reset the grid with demand. This is a necessary step before running the grid
    # here we use the same heat demand as when we build the grid as it is the first time the grid is run
    grid.reset(heat_demands)

    # run the grid of the whole 24 hours period.
    # we set the producer outlet temperature to always be 90 degree and electricity production to always be 20 MW
    grid.run(
        temp=[np.ones(config.TimeParameters["PlanningHorizon"]) * 90],
        electricity=[np.ones(config.TimeParameters["PlanningHorizon"]) * 20],
    )

    # or similarly you can do this to get ids
    obj_id_name = grid.get_id_name_all_obj()
    producer_id = [k for k, v in obj_id_name.items() if v == "CHP"][0]
    consumer_ids = [k for k, v in obj_id_name.items() if v == "Consumer"]
    edge_ids = [k for k, v in obj_id_name.items() if v == "Edge"]
    sup_edge_ids = edge_ids[0 : len(edge_ids) : 2]
    ret_edge_ids = edge_ids[1 : len(edge_ids) : 2]
    main_sup_edge_id = sup_edge_ids[0]
    main_ret_edge_id = ret_edge_ids[0]
    side_supply_edge_ids = sup_edge_ids[1:]
    side_ret_edge_ids = ret_edge_ids[1:]

    # get full basic status of the grid
    grid_status = grid.get_object_status(
        object_ids=consumer_ids,
        get_temp=True,
        get_ms=True,
        get_pressure=False,
        get_violation=False,
    )

    consumer1_sup_temp = grid_status[consumer_ids[0]]["Temp"][0]
    print("consumer 1 sup temp: ", consumer1_sup_temp)
    consumer2_sup_temp = grid_status[consumer_ids[1]]["Temp"][0]
    print("consumer 2 sup temp: ", consumer2_sup_temp)
    consumer3_sup_temp = grid_status[consumer_ids[2]]["Temp"][0]
    print("consumer 3 sup temp: ", consumer3_sup_temp)
