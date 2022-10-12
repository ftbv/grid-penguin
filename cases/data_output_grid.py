import numpy as np

# from perlin_noise import PerlinNoise
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

from .one_consumer import build_grid


def generate_data():
    horizon = 100

    # consumer_demand = (np.random.randn(horizon)*300 + 600)/10
    # consumer_demand[consumer_demand < 10] = 10
    consumer_demand = (np.random.uniform(size=horizon) * 1000 + 100) / 10

    grid = build_grid(consumer_demand)

    for producer in grid.producers:
        producer.opt_temp = np.full(len(consumer_demand), 90, dtype=float)

    grid.clear()
    grid.solve()

    for producer in grid.producers:

        data = [consumer_demand, producer.temp[1], producer.mass_flow[1]]

    return data


def generate_dataset():
    dataset = []
    max_data = torch.tensor([0, 0, 0])
    min_data = torch.tensor([np.inf, np.inf, np.inf])
    for _ in range(20):
        data = generate_data()
        data = torch.FloatTensor(data)
        data = torch.transpose(data, 0, 1)
        dataset.append(data)

        max_data = torch.maximum(torch.max(data, 0)[0], max_data)
        min_data = torch.minimum(torch.min(data, 0)[0], min_data)

    for i in range(len(dataset)):
        dataset[i] = ((dataset[i] - min_data) / (max_data - min_data)).unsqueeze(0)

    return torch.cat(dataset, 0)


class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.lstm1 = nn.LSTM(1, 100, 2)
        self.lstm2 = nn.LSTM(100, 1, 1)

        self.h1 = torch.randn(2, 1, 100)
        self.c1 = torch.randn(2, 1, 100)
        self.h2 = torch.randn(1, 1, 1)
        self.c2 = torch.randn(1, 1, 1)

    def forward(self, x):
        x, _ = self.lstm1(x, (self.h1, self.c1))
        output, _ = self.lstm2(x, (self.h2, self.c2))
        return output


mse = nn.MSELoss()
l1 = nn.L1Loss()

model = Net()

# optimizer = optim.Adadelta(model.parameters(), lr=0.001)
# optimizer = optim.Adam(model.parameters(), lr=0.001)
optimizer = optim.SGD(model.parameters(), lr=0.005, momentum=0.9)

dataset = generate_dataset()


for _ in range(300):
    r = torch.randperm(15)
    loss_total = 0
    for data in dataset[r]:

        output = model(data[:, 0].unsqueeze(1).unsqueeze(1))
        loss = l1(output, data[:, 1].unsqueeze(1).unsqueeze(1))
        loss.backward()
        optimizer.step()
        optimizer.zero_grad()
        loss_total += loss.item()

    print("train", loss_total / 15)

    with torch.no_grad():

        loss_total = 0
        for data in dataset[15:]:
            output = model(data[:, 0].unsqueeze(1).unsqueeze(1))

            loss = l1(output, data[:, 1].unsqueeze(1).unsqueeze(1))
            loss_total += loss.item()

        # print(output, data[2:].unsqueeze(1))
        print(loss_total / 5)
