import mesa
import networkx as nx
from agents import CommuterAgent, BusAgent

class IndoreTransitModel(mesa.Model):
    def __init__(self, num_commuters, num_buses):
        super().__init__()
        self.num_commuters = num_commuters
        self.commuters_lost = 0
        
        # 1. Create the Environment (A simple graph for now, later replace with OSMnx map of Indore)
        self.G = nx.cycle_graph(10) # Represents 10 connected bus stops
        self.grid = mesa.space.NetworkGrid(self.G)
        
        # 2. Scheduler
        self.schedule = mesa.time.RandomActivation(self)
        
        # 3. Add Buses
        for i in range(num_buses):
            bus = BusAgent(f"Bus_{i}", self, route_nodes=list(self.G.nodes))
            self.grid.place_agent(bus, 0) # Start at node 0
            self.schedule.add(bus)
            
        # 4. Add Commuters
        for i in range(self.num_commuters):
            dest = self.random.choice(list(self.G.nodes))
            commuter = CommuterAgent(f"Commuter_{i}", self, destination=dest)
            start_node = self.random.choice(list(self.G.nodes))
            self.grid.place_agent(commuter, start_node)
            self.schedule.add(commuter)

        # 5. Data Collector to track ridership factors
        self.datacollector = mesa.DataCollector(
            model_reporters={"Lost Commuters": "commuters_lost"}
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()