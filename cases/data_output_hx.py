import time
import numpy as np
from models.heat_exchanger import solve as heat_exchange
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.fc1 = nn.Linear(2, 100)
        self.fc1_1 = nn.Linear(100, 100)
        self.fc2 = nn.Linear(100, 2)

    def forward(self, x):
        x = self.fc1(x)
        x = F.relu(x)
        x = self.fc1_1(x)
        x = F.relu(x)
        x = self.fc2(x)
        output = F.sigmoid(x)
        return output


mse = nn.MSELoss()
l1 = nn.L1Loss()

max_mass_flow_p = 2000
setpoint_t_supply_s = 70
t_return_s = 45
heat_transfer_k = 207


data_file = []
start = time.time()
for _ in range(1000):
    t_supply_p = np.random.uniform() * 30 + 70
    mass_flow_s = np.random.uniform() * 1000

    (mass_flow_p, t_return_p, t_supply_s, q,) = heat_exchange(
        t_supply_p=t_supply_p,
        setpoint_t_supply_s=setpoint_t_supply_s,
        t_return_s=t_return_s,
        max_mass_flow_p=max_mass_flow_p,
        # Customer demand should be lower than what his pump allows.
        # Therefore, secondary mass flow can be very high
        mass_flow_s=mass_flow_s,
        surface_area=400,
        heat_transfer_k=heat_transfer_k,
    )
    data_file.append([t_supply_p, mass_flow_s, mass_flow_p, t_return_p])

print("hx", time.time() - start)

data_file = torch.FloatTensor(data_file)

data_min = torch.min(data_file, 0)[0]
data_max = torch.max(data_file, 0)[0]

data_file = (data_file - data_min) / (data_max - data_min)

train_data = data_file[:800]
test_data = data_file[800:]

model = Net()

# optimizer = optim.Adadelta(model.parameters(), lr=0.001)
# optimizer = optim.Adam(model.parameters(), lr=0.001)
optimizer = optim.SGD(model.parameters(), lr=0.005, momentum=0.9)


for _ in range(300):
    r = torch.randperm(800)
    for data in train_data[r]:
        output = model(data[:2].unsqueeze(0))
        loss = l1(output, data[2:].unsqueeze(0))
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()

    with torch.no_grad():
        start = time.time()
        for data in train_data[r]:
            output = model(data[:2].unsqueeze(0))

        loss_total = torch.tensor([0.0, 0.0])
        for data in test_data:
            output = model(data[:2].unsqueeze(0))

            loss = torch.abs(output[0] - data[2:]) * (data_max[2:] - data_min[2:])
            loss_total += loss

        # print('dl',time.time() - start)
        # print(output, data[2:].unsqueeze(0))
        print(loss_total / 200)
