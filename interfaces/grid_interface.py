import abc
import numpy as np
from typing import List, Dict, Optional, Union


class GridInterface(metaclass=abc.ABCMeta):
    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, "reset")
            and callable(subclass.reset)
            and hasattr(subclass, "run")
            and callable(subclass.run)
            and hasattr(subclass, "get_object_status")
            and callable(subclass.get_object_status)
            or NotImplemented
        )

    @abc.abstractmethod
    def reset(
        self,
        demands: Optional[list] = None,
        e_price: Optional[list] = None,
        pipe_states: Optional[list] = None,
    ) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def run(
        self,
        heat: Optional[list] = None,
        temp: Optional[list] = None,
        electricity: Optional[list] = None,
        producer_ids: Optional[list] = None,
        valve_pos: Optional[dict] = None,
        end_step = None,
    ) -> None:
        """
        e.g. Heat is either a 2-d list, with the first dimension being the different producers,
        second dimension being the time steps
        or a 1-d list with the first dimension being the different producers
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_object_status(
        self,
        object_ids: Optional[
            List[int]
        ] = None,  # if none, get status for all nodes and no edges
        start_step=0,
        end_step=None,  # if none, end at current simulation step
        get_temp: bool = True,
        get_ms: bool = False,
        get_pressure: bool = False,
        get_violation: bool = False,
    ) -> Dict[int, List]:
        """
        return dict: {node id: object_status}. Object status is a dictionary.
        Keys of this dictionary are Temp, Mass flow, Pressure and Violation (in this order).
        Values corresponding to respective keys are [temp (2d array), ms (2d array), pressure(2d array),
        violation (dictionary with key indicating type of violation, value is 1d array)]}.
        Values in violation are indicating how much the mentioned property
        is over limit (usually the original unit is kept, e.g. MWh)
        for violation types, check node.py and edge.py
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_pipe_states(
        self,
        time_step=0,
    ) -> List[List[List[float]]]:
        """
        Each plug state is a list of [mass, current temp, entry temp, entry step]
        The order of plugs: inlet -> outlet (first one is the closest to inlet)
        time_step can be confusing, 0 gets the initial plugs, 1 gets the plugs at time step 0 (after 1 time step run)
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_edge_heat_and_loss(
        self,
        edge_ids: Optional[List[int]] = None,
        level: Optional[int] = 0,
        level_time: Optional[int] = 0,
    ) -> Union[list, Dict[Union[int, str], list]]:
        """
        Get the heat in pipe and heat loss of the pipe
        level 0: total heat and/or loss of whole grid
        level 1: total heat and/or loss of the supply and return grid
        level 2: total heat and/or loss of each pipe
        level_time 0: sum over all time steps
        level_time 1: return each time step
        level_time 2: return current time step
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_detailed_margin(
        self,
        producer_ids: Optional[List[int]] = None,
        level: Optional[int] = 0,
        level_time: Optional[int] = 0,
    ) -> Union[float, Dict]:
        """
        level 0: total margin of whole grid
        level 1: total cost and profit of whole grid
        level 2: total cost and profit of each producer
        level 3: categorized cost and profit of each producer

        level_time 0: sum over all time steps
        level_time 1: return each time step
        level_time 2: return current time step

        the return is either level 0-0/2: "float" a number of total margin
        level 0-1: "list" a list of total margin on each time step
        level 1: Dict[str,Union[List,float]], keys are cost and profit
        level 2: Dict[int, Union[List,float]], keys are producer ids
        level 3: Dict[int, Dict[str, Dict[str, Union[list, float]]]] with the first key being producer id and
        second key being either cost or profit and the third key being type of cost
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_id_name_all_obj(self) -> Dict[int, str]:
        """
        Get the id and class name of all objects in the grid
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_actual_delivered_heat(self) -> Dict[int, np.array]:
        """
        Get actual delivered heat to each consumer (in MW). The form is a dictionary with the key corresponding to the
        consumer id, and the value corresponding to the array of delivered heat.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_sec_supply_in_temp(self) -> Dict[int, np.array]:
        """
        Get secondary side supply inlet temperature (at the exit of heat exchanger station)
        for each consumer.
        """
        raise NotImplementedError
