# GridPenguin

**Introduction**

GridPenguin is a powerful and comprehensive tool to simulate a district heating system(DHS) with both good accuracy and high speed. We designed GridPenguin as a benchmark tool to compare different DHS optimization algorithms. It also give possibilities to new optimization algorithms that requires a fast and iterative process with a DHS simulator, e.g. data-driven machine learning algorithms. For a detailed comprehensive documentary about the physical & computational logic and scientific significiency, please go to our publication at [NEFI](https://www.nefi.at/en/nefi-conference/program): [presentation](https://docs.google.com/presentation/d/1fRGLz8aZm_QjNs9TWhG1wBKI8jphdJccZvikpo7tJmo/edit?usp=sharing) and [paper](https://drive.google.com/file/d/1ZvOwysejnq809xG8z2_dnh55tQESIpf1/view?usp=sharing).

**Dependencies**
- Python 3.10.6
- Numpy 1.23.3
- Scipy 1.9.1
- BeautifulTable 1.1.0

**Get Started**

Install local package with `pip install -e .`
Go to one folder above the root, then run `$python -m grid-penguin.examples.example_one_consumer`. This script build and run a one-consumer DHS with demand, supply temperature etc. specified in the script.
You can also run a 3-consumer DHS by `$python -m grid-penguin.examples.example_3_consumers`.

**Directory Structure**
- **Interfaces**: the interfaces of GridPenguin
  - grid_interface.py
- **Case**: construction of different network structure
  - one_consumer.py: network with one producer, one consumer and two pipes
  - parallel_consumer.py: network with parallel multiple consumers, one producer
- **Models**: building blocks of the network
  - **Producers**: models of the producer, currently only contains the CHP
    - CHP.py: model of the CHP
  - grid.py: container for all nodes and edges
  - producer.py: production unit (CHP is also a producer, but here the producer is modeled much simplified)
  - consumer.py: end consumer that has heat demand
  - edge.py: water pipes
  - transfer.py: Heat exchange station
- **Util**: utilities and configurations
- **Wanda_compare**: to build dummy grid and compare performance with Wanda

**Support**
For questions and issues, please open a github issue.
