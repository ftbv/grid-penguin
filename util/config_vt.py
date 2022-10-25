from pathlib import Path

# =========================================================
# File Path
# =========================================================
Dataset = {
    "Path": (Path(__file__).parents[2] / "data"),
    "FileName": "processed_data.csv",
    "train_test_split_point": 0.8,
}

Paths = {
    "Results": (Path(__file__).parents[2] / "results"),
    "Plots": (Path(__file__).parents[2] / "plots"),
}

# =========================================================
# Global Parameters
# =========================================================
PhysicalProperties = {
    "Density": 963,
    "HeatCapacity": 4181.3,
    "MaxTemp": 120,
    "MinSupTemp": 70,
    "EnergyUnitConversion": 10 ** 6,  # The scale to convert given energy unit to Watt
}

GridProperties = {"ConsumerNum": 1}

GridProperties["PipeNum"] = (
    2 * GridProperties["ConsumerNum"]
    if GridProperties["ConsumerNum"] == 1
    else 2 * (GridProperties["ConsumerNum"] + 1)
)

TimeParameters = {
    "TimeInterval": 900,  # seconds
    "PlanningHorizon": 24 * 4,  # steps
    "ActionHorizon": 1 * 4,  # steps
}

# =========================================================
# Grid Parameters
# =========================================================
CHPPreset1 = {
    "CHPType": "keypts",
    "OperationRegion": [[10, 5], [0, 10], [0, 50], [70, 35]],  # Heat, power. MW
    "Efficiency": 1,
    "FuelCost": [8.1817, 38.1805],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": 3,
}

ProducerPreset1 = {
    "Type": "CHP",
    "Parameters": CHPPreset1,
    "PumpEfficiency": 1,
    "ControlWithTemp": True,
}

ConsumerPreset1 = {
    "k": 271.3,
    "q": 1.2,
    "SurfaceArea": 40,
    "TempReturnSeconary": 45,
    "SetPointTempSupplySecondary": 70,
    "MaxMassFlowPrimary": 805.15,
    "MinTempSupplyPrimary": 70,
    "FixPressureLoad": 100000,
}

PipePreset1 = {
    "Diameter": 0.5958,
    "Length": 12000,
    "ThermalResistance": 1.36,  # in k*m/W, = 1/U
    "InitialTemperature": 105,
    "EnvironmentTemperature": 10,
    "MaxFlowSpeed": 3,
    "MinFlowSpeed": 0,
    "FrictionCoefficient": 1.29 * 1.414,
}

PipePreset2 = {
    "Diameter": 0.5958,
    "Length": 12000,
    "ThermalResistance": 1.36,  # in k*m/W, = 1/U
    "InitialTemperature": 50,
    "EnvironmentTemperature": 10,
    "MaxFlowSpeed": 3,
    "MinFlowSpeed": 0,
    "FrictionCoefficient": 1.29 * 1.414,
}

# supply side edge
PipePreset3 = {
    "Diameter": 0.2,
    "Length": 3000,
    "ThermalResistance": 1.1,  # in k*m/W, = 1/U
    "InitialTemperature": 90,
    "EnvironmentTemperature": 10,
    "MaxFlowSpeed": 3,
    "MinFlowSpeed": 0,
    "FrictionCoefficient": 1.29 * 2,
}

# return side edge
PipePreset4 = {
    "Diameter": 0.2,
    "Length": 3000,
    "ThermalResistance": 1.1,  # in k*m/W, = 1/U
    "InitialTemperature": 50,
    "EnvironmentTemperature": 10,
    "MaxFlowSpeed": 3,
    "MinFlowSpeed": 0,
    "FrictionCoefficient": 1.29 * 2,
}
# GridParameters = {
#   'Producers': [
#     {
#       'Type': 'CHP',
#       'Parameters': CHPPreset1,
#       'PumpEfficiency': 1,
#       'ControlWithTemp': True,
#     }
#   ],
#   'Consumers': [
#     HXPreset1,
#   ],
#   'Pipes': [
#     PipePreset1,
#     PipePreset2,
#   ],
# }
