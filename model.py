import mesa
import networkx as nx
import osmnx as ox
from agents import CommuterAgent, BusAgent

class IndoreTransitModel(mesa.Model):
    def __init__(self, num_commuters, num_buses):
        super().__init__()
        self.num_commuters = num_commuters
        self.commuters_lost = 0
        
        print("Downloading Indore street data...")
        self.G = ox.graph_from_address('Palasia Square, Indore, India', dist=300, network_type='drive')
        self.G = nx.Graph(self.G) 
        
        # Keep our safe integer IDs!
        self.G = nx.convert_node_labels_to_integers(self.G)
        
        self.grid = mesa.space.NetworkGrid(self.G)
        self.schedule = mesa.time.RandomActivation(self)
        
        nodes = list(self.G.nodes)
        
        # --- NEW: Initialize an empty queue list for EVERY intersection ---
        self.stop_queues = {node: [] for node in nodes}
        
        # Add Buses
        for i in range(num_buses):
            bus = BusAgent(f"Bus_{i}", self, route_nodes=nodes)
            start_node = self.random.choice(nodes)
            self.grid.place_agent(bus, start_node)
            self.schedule.add(bus)
            
        # Add Commuters
        for i in range(self.num_commuters):
            dest = self.random.choice(nodes)
            commuter = CommuterAgent(f"Commuter_{i}", self, destination=dest)
            start_node = self.random.choice(nodes)
            self.grid.place_agent(commuter, start_node)
            self.schedule.add(commuter)
            
            # --- NEW: Commuter officially joins the back of the queue at their start node ---
            self.stop_queues[start_node].append(commuter)

        self.datacollector = mesa.DataCollector(
            model_reporters={"Lost Commuters": "commuters_lost"}
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()