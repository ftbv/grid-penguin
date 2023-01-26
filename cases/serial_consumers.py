# grid for one producer and multiple consumers
# that has exactly the same distance to the producer
from ..models import Grid, Producer, Consumer, Edge, CHP
from ..models import Branch, Junction


def build_grid(
    consumer_demands,
    electricity_prices,
    config,
):
    """
    Building the grid object with multiple consumers.
    """
    consumer_numbers = len(consumer_demands)  # number of consumers
    producer_params = config.ProducerPreset1
    consumer_params = config.ConsumerPreset1
    sup_main_pipe_params = config.PipePreset1
    ret_main_pipe_params = config.PipePreset2
    sup_side_pipes_params = [config.PipePreset3, config.PipePreset5]
    ret_side_pipes_params = [config.PipePreset4, config.PipePreset6]
    physical_properties = config.PhysicalProperties
    time_params = config.TimeParameters

    blocks = consumer_demands[0].shape[0]

    grid = Grid(  # empty grid
        interval_length=time_params["TimeInterval"],  # 60 min
    )

    producer = CHP(
        CHPPreset=producer_params["Generators"][0],
        blocks=blocks,  # time steps (24 hours -> 24 blocks)
        heat_capacity=physical_properties[
            "HeatCapacity"
        ],  # in J/kg/K # for the water
        temp_upper_bound=physical_properties["MaxTemp"],
        pump_efficiency=producer_params["PumpEfficiency"],
        density=physical_properties["Density"],
        control_with_temp=producer_params["ControlWithTemp"],
        energy_unit_conversion=physical_properties["EnergyUnitConversion"],
    )
    grid.add_node(producer)  # characterized with temperature


    sup_branch = Branch(blocks, out_slots_number=consumer_numbers)
    grid.add_node(sup_branch)
    ret_junction = Junction(blocks, in_slots_number=consumer_numbers)
    grid.add_node(ret_junction)

    consumers = []
    for i in range(consumer_numbers):
        consumer = Consumer(
            demand=consumer_demands[i].copy(),
            heat_capacity=physical_properties["HeatCapacity"],  # in J/kg/K
            max_mass_flow_p=consumer_params["MaxMassFlowPrimary"],
            surface_area=consumer_params["SurfaceArea"],  # in m^2
            heat_transfer_q=consumer_params["q"],  # See Palsson 1999 p45
            heat_transfer_k=consumer_params["k"],  # See Palsson 1999 p51
            min_supply_temp=consumer_params["MinTempSupplyPrimary"],
            pressure_load=consumer_params["FixPressureLoad"],
            setpoint_t_supply_s=consumer_params["SetPointTempSupplySecondary"],
            t_return_s=consumer_params["TempReturnSeconary"],
            energy_unit_conversion=physical_properties["EnergyUnitConversion"],
        )
        grid.add_node(consumer)
        consumers.append(consumer)

    edges = []
    """
    Add the main supply and return edge. The main supply edge connects Producer and Branch.
    The main return edge connects Junction and Producer.
    """
    for pipe_params in [sup_main_pipe_params, ret_main_pipe_params]:
        edge = Edge(
            blocks=blocks,
            diameter=pipe_params["Diameter"],  # in meters
            length=pipe_params["Length"],  # in meters
            thermal_resistance=pipe_params["ThermalResistance"],  # in k*m/W
            historical_t_in=pipe_params["InitialTemperature"],  # in ºC
            heat_capacity=physical_properties["HeatCapacity"],  # in J/kg/K
            density=physical_properties["Density"],  # in kg/m^3
            t_ground=pipe_params["EnvironmentTemperature"],  # °C
            max_flow_speed=pipe_params["MaxFlowSpeed"],  # m/s
            min_flow_speed=pipe_params["MinFlowSpeed"],
            friction_coefficient=pipe_params["FrictionCoefficient"],  # (kg*m)^-1
            energy_unit_conversion=physical_properties["EnergyUnitConversion"],
        )
        edges.append(edge)
        grid.add_edge(edge)
    """
    Main supply edge has the producer on slot 1, and Branch on slot 0.
    """
    edges[0].link(
        nodes=(
            (producer, 1),
            (sup_branch, 0),
        )
    )
    """
    Main return edge has Junction on slot=number of consumers, and Producer on slot 0.
    """
    edges[1].link(
        nodes=(
            (ret_junction, 0),
            (producer, 0),
        )
    )

    for i, consumer in enumerate(consumers):
        sup_side_pipe_params = sup_side_pipes_params[i]
        ret_side_pipe_params = ret_side_pipes_params[i]
        sup_side_edge = Edge(
            blocks=blocks,
            diameter=sup_side_pipe_params["Diameter"],  # in meters
            length=sup_side_pipe_params["Length"],  # in meters
            thermal_resistance=sup_side_pipe_params["ThermalResistance"],  # in k*m/W
            historical_t_in=sup_side_pipe_params["InitialTemperature"],  # in ºC
            heat_capacity=physical_properties["HeatCapacity"],  # in J/kg/K
            density=physical_properties["Density"],  # in kg/m^3
            t_ground=sup_side_pipe_params["EnvironmentTemperature"],  # °C
            max_flow_speed=sup_side_pipe_params["MaxFlowSpeed"],  # m/s
            min_flow_speed=sup_side_pipe_params["MinFlowSpeed"],
            friction_coefficient=sup_side_pipe_params[
                "FrictionCoefficient"
            ],  # (kg*m)^-1
            energy_unit_conversion=physical_properties["EnergyUnitConversion"],
        )
        grid.add_edge(sup_side_edge)

        ret_side_edge = Edge(
            blocks=blocks,
            diameter=ret_side_pipe_params["Diameter"],  # in meters
            length=ret_side_pipe_params["Length"],  # in meters
            thermal_resistance=ret_side_pipe_params["ThermalResistance"],  # in k*m/W
            historical_t_in=ret_side_pipe_params["InitialTemperature"],  # in ºC
            heat_capacity=physical_properties["HeatCapacity"],  # in J/kg/K
            density=physical_properties["Density"],  # in kg/m^3
            t_ground=ret_side_pipe_params["EnvironmentTemperature"],  # °C
            max_flow_speed=ret_side_pipe_params["MaxFlowSpeed"],  # m/s
            min_flow_speed=ret_side_pipe_params["MinFlowSpeed"],
            friction_coefficient=ret_side_pipe_params[
                "FrictionCoefficient"
            ],  # (kg*m)^-1
            energy_unit_conversion=physical_properties["EnergyUnitConversion"],
        )
        grid.add_edge(ret_side_edge)

        sup_side_edge.link(
            nodes=(
                (sup_branch, i + 1),
                (consumer, 0),
            )
        )
        ret_side_edge.link(
            nodes=(
                (consumer, 1),
                (ret_junction, i+1),
            )
        )

    grid.link_nodes(False)

    return grid
