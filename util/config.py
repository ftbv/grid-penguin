from pathlib import Path


# =========================================================
# Global Parameters
# =========================================================
PhysicalProperties = {
    "Density": 963,
    "HeatCapacity": 4181.3, # J/(kg*C)
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
    "TimeInterval": 3600,  # seconds
    "PlanningHorizon": 24,  # h
    "ActionHorizon": 1,  # h
}

# =========================================================
# Grid Parameters
# =========================================================
# generator scale muliplier
gsm = 1

Generator1 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.12*gsm,0],[0.75*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.81,
    "FuelCost": [1, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":505.1*gsm,
    "InitialStatus":True,
}

Generator2 = Generator1
Generator3 = Generator1

Generator4 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.12*gsm,0],[0.47*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.89,
    "FuelCost": [1.64, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":154*1.64*gsm,
    "InitialStatus":True,
}

Generator5 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.79*gsm,0],[2.74*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.89,
    "FuelCost": [5.86, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":43.1*5.86*gsm,
    "InitialStatus":True,
}

Generator6 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.39*gsm,0],[1.73*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.89,
    "FuelCost": [6.34, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":4*6.34*gsm,
    "InitialStatus":True,
}

Generator7 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.55*gsm,0],[1.2*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.89,
    "FuelCost": [6.34, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":2*6.34*gsm,
    "InitialStatus":False,
}

Generator8 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.2*gsm,0],[1.14*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.87,
    "FuelCost": [8.33, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":3*8.33*gsm,
    "InitialStatus":False,
}

Generator9 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.2*gsm,0],[1.37*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.87,
    "FuelCost": [8.51, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":3*8.51*gsm,
    "InitialStatus":False,
}

Generator10 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.27*gsm,0],[2.04*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.87,
    "FuelCost": [8.59, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":2.9*8.59*gsm,
    "InitialStatus":False,
}

Generator11 = Generator10

Generator12 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.12*gsm,0],[1.14*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.87,
    "FuelCost": [9.6, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":1.3*9.6*gsm,
    "InitialStatus":False,
}

Generator13 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.12*gsm,0],[1.37*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.87,
    "FuelCost": [9.82, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":1.3*9.82*gsm,
    "InitialStatus":False,
}

Generator14 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.0*gsm,0],[0.98*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.87,
    "FuelCost": [14.17, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":0.89*14.17*gsm,
    "InitialStatus":False,
}

Generator15 = {
    "CHPType": "keypts",
    "OperationRegion": [[0.0*gsm,0],[1.37*gsm,0]],  # Heat, power. MW
    "Efficiency": 0.87,
    "FuelCost": [14.17, 0],
    "MaxRampRateQ": -1,
    "MaxRampRateE": -1,
    "MaxRampRateTemp": -1,
    "StartupCost":0.89*14.17*gsm,
    "InitialStatus":False,
}

ProducerPreset1 = {
    "Generators": [
        Generator1,
        Generator2,
        Generator3,
        Generator4,
        Generator5,
        Generator6,
        Generator7,
        Generator8,
        Generator9,
        Generator10,
        Generator11,
        Generator12,
        Generator13,
        Generator14,
        Generator15,
    ],
    "PumpEfficiency": 1,
    "ControlWithTemp": True,
}

ProducerPreset1 = {
    "Type": "CHP",
    "Parameters": CHPPreset1,
    "PumpEfficiency": 1,
    "ControlWithTemp": True,
}

ConsumerPreset1 = {
    "k": 5 * 10 ** 6 / 400 * (400 ** (-0.8) + 400 ** (-0.8)),
    "q": 0.8,
    "SurfaceArea": 400,
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
    "InitialTemperature": 90,
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
    "Length": 6000,
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
    "Length": 6000,
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