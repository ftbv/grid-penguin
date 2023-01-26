# This class holds all nodes and edges in the grid and how they are linked.
# It also manages solving the grid

import numpy as np  # type: ignore

from typing import List, Iterator, Tuple, Dict, Optional, Union
from functools import cached_property

from .node import Node
from .edge import Edge
from .grid_object import GridObject
from .timing import Timing
from .heat_exchanger import timing as heat_exchanger_timing
from .edge import timing as edge_timing
from ..interfaces.grid_interface import GridInterface

import sys
import traceback


class Grid(GridInterface):
    def __init__(
        self,
        interval_length: int,  # in sec
    ) -> None:
        self.nodes: List[Node] = []
        self.node_dict: Dict[int, int] = {}

        self.edges: List[Edge] = []
        self._solvable_objects: List[Tuple[GridObject, int, float]] = []

        self._interval_length = interval_length

    def solvable(self, object: GridObject, slot: int, mass_flow: float) -> None:
        """
        Appends object, its slot and mass flow to the list of _solvable_objects of the class Grid.
        """
        self._solvable_objects.append((object, slot, mass_flow))

    def add_node(self, node: Node) -> None:
        """
        Adding node to the list of nodes. Adding node to the grid.
        """
        self.nodes.append(node)

        self.node_dict[node.id] = len(self.nodes) - 1
        node.add_to_grid(
            self.solvable,
            self._interval_length,
        )

    def add_edge(self, edge: Edge) -> None:
        self.edges.append(edge)
        edge.add_to_grid(
            self.solvable,
            self._interval_length,
        )

    def link_nodes(self, print_debug: bool = False) -> None:
        """pressure_load
        If you only explicitly link edges, calling this function is required
        """
        timing = Timing()

        edges_per_node: List[List[Tuple[Edge, int]]] = [[] for x in self.nodes]
        for edge in self.edges:
            for (edge_node, slot) in edge.nodes:
                i = self.node_dict[edge_node.id]
                edges_per_node[i].append((edge, slot))

        def by_slot(edge: Tuple[Edge, int]) -> int:
            return edge[1]

        for i, edges_for_node in enumerate(edges_per_node):
            edges_for_node.sort(key=by_slot)
            edges: List[Edge] = []

            for e_f_n in edges_for_node:
                edges.append(e_f_n[0])
            node = self.nodes[i]
            node.link(tuple(edges))

        if print_debug:
            print("Linking: {:.1f} sec".format(timing.get()))

    def reset(
        self,
        demands: Optional[list] = None,
        e_price: Optional[list] = None,
        pipe_states: Optional[list] = None,
    ) -> None:
        if demands is not None:
            for demand, consumer in zip(demands, self.consumers):
                consumer.update_demand(demand)

        if pipe_states is not None:
            for pipe_state, edge in zip(pipe_states, self.edges):
                edge.set_initial_plugs(pipe_state)

        if e_price is not None:
            for price, producer in zip(e_price, self.producers):
                producer.e_price = np.array(price)

        self.clear()

    def run(
        self,
        heat: Optional[list] = None,
        temp: Optional[list] = None,
        electricity: Optional[list] = None,
        producer_ids: Optional[list] = None,
        valve_pos: Optional[dict] = None,
        end_step: Optional[int] = None,
    ) -> None:

        opt_time = GridObject._current_step
        if producer_ids is None:
            producer_ids = [p.id for p in self.producers]

        if heat is not None:
            conditions = heat
            cond_type = 'q'
        else:
            conditions = temp
            cond_type = 'temp'

        for c, producer_id in zip(conditions, producer_ids):
            producer = self.get_object(producer_id)
            assert producer.type_name == "Producer"
            val = getattr(producer, cond_type)
            if not isinstance(c, (list, np.ndarray)):
                if cond_type == 'temp':
                    val[1, opt_time] = c
                else:
                    val[opt_time] = c

                run_step = 1
            else:
                run_step = len(c)
                if cond_type == 'temp':
                    val[1, opt_time: (opt_time + run_step)] = c
                else:
                    val[opt_time: (opt_time + run_step)] = c

        if electricity is not None:
            for e, id in zip(electricity, producer_ids):
                if e is not None:
                    producer = self.get_object(id)
                    if not isinstance(e, (list, np.ndarray)):
                        assert run_step == 1
                        producer.E[opt_time] = e
                    else:
                        assert run_step > 1
                        producer.E[opt_time: (opt_time + run_step)] = e

        if valve_pos is not None:
            for n_id, v_pos in valve_pos.items():
                split = self.get_object(n_id)
                if not isinstance(e, (list, np.ndarray)):
                    assert run_step == 1
                    split.valve_position[:,opt_time] = v_pos
                else:
                    assert run_step > 1
                    split.valve_position[:, opt_time : (opt_time + run_step)] = v_pos

        start_step = opt_time
        if end_step is None:
            end_step = min(start_step + run_step, self.blocks)

        while opt_time < end_step:
            self._solve()
            opt_time += 1

        return None

    def get_object_status(
        self,
        object_ids: Optional[List[int]] = None,
        start_step=0,
        end_step=None,
        get_temp: bool = True,
        get_ms: bool = False,
        get_pressure: bool = False,
        get_violation: bool = False,
    ) -> Dict[int, List]:
        if object_ids is None:
            object_query_queue = self.nodes
        else:
            object_query_queue = [self.get_object(id) for id in object_ids]

        end_step = GridObject._current_step if end_step is None else end_step

        objects_status = {}
        for obj in object_query_queue:
            temp = obj.temp[:, start_step:end_step] if get_temp else []
            ms = obj.mass_flow[:, start_step:end_step] if get_ms else []
            pressure = obj.pressure[:, start_step:end_step] if get_pressure else []
            violation = {}
            if get_violation:
                for key, arr in obj.violations.items():
                    violation.update({key: arr[start_step:end_step]})

            object_status = {
                "Temp": temp,
                "Mass flow": ms,
                "Pressure": pressure,
                "Violation": violation,
            }
            objects_status[obj.id] = object_status

        return objects_status

    def get_pipe_states(self, time_step=0):
        pipe_conditions = []
        for edge in self.edges:
            pipe_conditions.append(edge.get_plugs_condition(time_step))

        return pipe_conditions

    def get_edge_heat_and_loss(
        self,
        edge_ids: Optional[List[int]] = None,
        level: Optional[int] = 0,
        level_time: Optional[int] = 0,
    ) -> Union[list, Dict[Union[int, str], list]]:
        heat_dict = {}
        for edge in self.edges:
            if edge_ids is not None:
                if edge.id not in edge_ids:
                    continue
            if level_time == 0:
                heat_dict[edge.id] = [
                    np.sum(edge.heat_in_pipe[: GridObject.current_step]),
                    np.sum(edge.heat_loss[: GridObject.current_step]),
                ]
            elif level_time == 1:
                heat_dict[edge.id] = [
                    edge.heat_in_pipe[: GridObject._current_step],
                    edge.heat_loss[: GridObject._current_step],
                ]
            else:
                assert level_time == 2
                heat_dict[edge.id] = [
                    edge.heat_in_pipe[GridObject._current_step - 1],
                    edge.heat_loss[GridObject._current_step - 1],
                ]

        if level == 2:
            return heat_dict

        elif level == 1:
            heat_supply = []
            loss_supply = []
            heat_return = []
            loss_return = []
            for edge in self.edges:
                if edge.is_supply:
                    heat_supply.append(heat_dict[edge.id][0])
                    loss_supply.append(heat_dict[edge.id][1])
                else:
                    heat_return.append(heat_dict[edge.id][0])
                    loss_return.append(heat_dict[edge.id][1])

            heat_dict = {"supply": [
                np.sum(heat_supply, axis=0),
                np.sum(loss_supply, axis=0),
            ], "return": [
                np.sum(heat_return, axis=0),
                np.sum(loss_return, axis=0),
            ]}
            return heat_dict

        elif level == 0:
            heat = np.sum([h[0] for h in heat_dict.values()], axis=0)
            loss = np.sum([h[1] for h in heat_dict.values()], axis=0)
            return [heat, loss]

        raise Exception

    def get_detailed_margin(
        self,
        producer_ids: Optional[List[int]] = None,
        level: Optional[int] = 0,
        level_time: Optional[int] = 0,
    ) -> Union[float, Dict]:
        margin3 = {}
        if producer_ids is None:
            producer_queue = [producer for producer in self.producers]
        else:
            producer_queue = [self.get_object(id) for id in producer_ids]

        for p in producer_queue:
            margin3[p.id] = p.get_margin(level_time)

        if level == 3:
            return margin3
        else:
            margin2 = {}
            for p_id, p_margin in margin3.items():
                margin2[p_id] = {}
                margin2[p_id]["cost"] = np.sum(
                    [cost for cost_type, cost in p_margin["cost"].items()], axis=0
                )
                margin2[p_id]["profit"] = p_margin["profit"]

            if level == 2:
                return margin2
            else:
                margin1 = {
                    "cost": np.sum(
                        [p_m["cost"] for p_id, p_m in margin2.items()], axis=0
                    ),
                    "profit": np.sum(
                        [p_m["profit"] for p_id, p_m in margin2.items()], axis=0
                    )
                }

                if level == 1:
                    return margin1
                else:
                    return -margin1["cost"] + margin1["profit"]

    def get_id_name_all_obj(self) -> Dict[int, str]:
        id_name_dict = {}
        for node in self.nodes:
            id_name_dict[node.id] = type(node).__name__

        for edge in self.edges:
            id_name_dict[edge.id] = type(edge).__name__

        return id_name_dict

    def get_actual_delivered_heat(self):
        actual_delivered_heat = {}
        for consumer in self.consumers:
            actual_delivered_heat[consumer.id] = consumer.q
        return actual_delivered_heat

    def get_sec_supply_in_temp(self):
        s_supply_temp = {}
        for consumer in self.consumers:
            s_supply_temp[consumer.id] = consumer.s_supply_temp
        return s_supply_temp


    def clear(self, print_debug: bool = False) -> None:
        timing = Timing()
        heat_exchanger_timing.restart()
        edge_timing.restart()

        GridObject.reset_step()

        for node in self.nodes:
            node.clear()

        for edge in self.edges:
            edge.clear()

        if print_debug:
            print("Clearing: {:.1f} sec".format(timing.get()))

    def solve_one_step(self, heat=None, temp=None):
        if heat is not None:
            for h, producer in zip(heat, self.producers):
                producer.q[GridObject._current_step] = h
        else:
            assert temp is not None
            for t, producer in zip(temp, self.producers):
                producer.temp[0, GridObject._current_step] = t
        condition_flag = self._solve()  # step is increased here

        inlet_temp, outlet_temp, mass_flow = [], [], []
        pipe_conditions = []
        for edge in self.edges:
            inlet_temp.append(edge.temp[0, GridObject._current_step - 1])
            outlet_temp.append(edge.temp[1, GridObject._current_step - 1])
            mass_flow.append(edge.mass_flow[GridObject._current_step - 1])
            pipe_conditions.append(edge.get_plugs_condition())

        heat_delivered = [c.q[GridObject._current_step - 1] for c in self.consumers]

        inlet_temp = np.array(inlet_temp)
        outlet_temp = np.array(outlet_temp)
        mass_flow = np.array(mass_flow)
        heat_delivered = np.array(heat_delivered)

        return (
            inlet_temp,
            outlet_temp,
            mass_flow,
            heat_delivered,
            pipe_conditions,
            condition_flag,
        )

    # the function should only be called after solve_one_step
    def get_temp_at_nodes(self):
        inlet_temp, outlet_temp = [], []
        for node in self.nodes:
            inlet_temp.append(node.temp[0, GridObject._current_step - 1])
            outlet_temp.append(node.temp[1, GridObject._current_step - 1])

        return inlet_temp, outlet_temp

    def solve(
        self,
        print_debug: bool = False,
    ) -> None:

        timing = Timing()
        condition_flags = []
        opt_time = 0
        while opt_time < self.blocks:
            # print('Solving time {}'.format(opt_time))
            try:
                condition_flag = self._solve()
                condition_flags.append(condition_flag)
            except Exception as e:
                print(e)
                print("".join(traceback.format_tb(e.__traceback__)))
                # self.debug()
                sys.exit(1)

            opt_time += 1

        if print_debug:
            self.debug_solve(timing)

        return np.array(condition_flags)

    def _solve(self) -> None:
        # to avoid high recursion depth, collect every solvable node/ edge here
        for consumer in self.consumers:
            consumer.solve()

        while self._solvable_objects:
            (obj, slot, mass_flow) = self._solvable_objects.pop(0)
            obj.set_mass_flow(slot, mass_flow)

        # get producer cost
        for producer in self.producers:
            producer.solve()

        GridObject.increase_step()

    # call after _solve
    def get_condition_violation_one_step(self):
        violation = {}
        for i, consumer in enumerate(self.consumers):
            violation["consumer%s" % i] = max(
                consumer.demand[GridObject._current_step - 1]
                - consumer.q[GridObject._current_step - 1],
                0,
            )
            if violation["consumer%s" % i] < 1:
                violation["consumer%s" % i] = 0

        for i, producer in enumerate(self.producers):
            violation["producer%s" % i] = max(
                producer.virtual_temp_sup[GridObject._current_step - 1]
                - producer.temp_upper_bound,
                0,
            )

        for i, edge in enumerate(self.edges):
            violation["edge%s" % i] = max(
                edge.flow_speed[GridObject._current_step - 1] - edge.max_flow_speed, 0
            ) + min(
                edge.flow_speed[GridObject._current_step - 1] - edge.min_flow_speed, 0
            )

        return violation

    def debug(self, csv: bool = False) -> None:
        for node in self.nodes:
            node.debug(csv=csv)

        for edge in self.edges:
            edge.debug(csv=csv)

    @staticmethod
    def debug_solve(timing: Timing):
        print("Solving: {:.1f} sec".format(timing.get()))
        print(
            "..of which heat exchanger: {:.1f} sec".format(
                heat_exchanger_timing.get()
            )
        )
        print("..of which long edge solving: {:.1f} sec".format(edge_timing.get()))

    def unfulfilled_demand(self, up_to_step: Optional[int]) -> float:
        unfulfilled_demand: float = 0
        for consumer in self.consumers:
            unfulfilled_demand += consumer.unfulfilled_demand(up_to_step)
        return unfulfilled_demand  # in MWh

    def get_object(self, id):
        for node in self.nodes:
            if node.id == id:
                return node

        for edge in self.edges:
            if edge.id == id:
                return edge

        raise Exception("Object id not found")

    @property
    def producers(self) -> Iterator[Node]:
        return filter(
            lambda n: (
                type(n).__name__ == "Producer"
                or "Producer" in [base.__name__ for base in type(n).__bases__]
            ),
            self.nodes,
        )

    @property
    def consumers(self) -> Iterator[Node]:
        return filter(
            lambda n: type(n).__name__ == "Consumer",
            self.nodes,
        )

    @cached_property
    def consumers_id(self):
        ids = self.get_id_name_all_obj()
        return [id for id, name in ids.items() if name == "Consumer"]

    @cached_property
    def producers_id(self):
        ids = self.get_id_name_all_obj()
        return [
            id for id, name in ids.items() if (name == "CHP") | (name == "producer")
        ]

    @property
    def blocks(self) -> int:
        if len(self.nodes) == 0:
            return 0

        return self.nodes[0].blocks
