from ..models import Grid, Producer, Consumer, Edge, CHP


def build_grid(
    consumer_demands,
    electricity_prices,
    config,
):
    consumer_demand = consumer_demands[0]
    producer_params = config.ProducerPreset1
    consumer_params = config.ConsumerPreset1
    sup_pipe_params = config.PipePreset1
    ret_pipe_params = config.PipePreset2
    physical_properties = config.PhysicalProperties
    time_params = config.TimeParameters

    blocks = consumer_demand.shape[0]

    grid = Grid(  # empty grid
        interval_length=time_params["TimeInterval"],  # 60 min
    )

    if producer_params["Type"] == "CHP":
        producer = CHP(
            CHPPreset=producer_params["Parameters"],
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
    else:
        raise Exception("producer type not implemented")

    consumer = Consumer(
        demand=consumer_demand.copy(),
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

    edges = []
    for pipe_params in [sup_pipe_params, ret_pipe_params]:
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

    edges[0].link(
        nodes=(  # 0 is a slot
            (producer, 1),
            (consumer, 0),
        )
    )

    edges[1].link(
        nodes=(  # 1 is a slot
            (consumer, 1),
            (producer, 0),
        )
    )

    grid.link_nodes(False)

    return grid
