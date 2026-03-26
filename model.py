import mesa
import networkx as nx
import osmnx as ox
from agents import CommuterAgent, BusAgent

def get_commuters_in_bus(model):
    return sum(1 for a in model.schedule.agents 
               if type(a).__name__ == "CommuterAgent" and a.state == "in_bus")

def get_commuters_waiting(model):
    # We now count people walking to the stop as "waiting" for chart purposes
    return sum(1 for a in model.schedule.agents 
               if type(a).__name__ == "CommuterAgent" and a.state in ["waiting", "walking_to_stop", "evaluating"])

class IndoreTransitModel(mesa.Model):
    def __init__(self, num_commuters, num_buses):
        super().__init__()
        self.num_commuters = num_commuters
        self.commuters_lost = 0
        
        print("Downloading Indore street data...")
        self.G = ox.graph_from_address('Palasia Square, Indore, India', dist=500, network_type='drive')
        self.G = nx.Graph(self.G) 
        self.G = nx.convert_node_labels_to_integers(self.G)
        
        self.grid = mesa.space.NetworkGrid(self.G)
        self.schedule = mesa.time.RandomActivation(self)
        
        nodes = list(self.G.nodes)
        self.stop_queues = {node: [] for node in nodes}
        
        # Generate predefined BRTS Routes
        self.routes = []
        for _ in range(2): 
            longest_path = []
            for _ in range(15):
                n1, n2 = self.random.choice(nodes), self.random.choice(nodes)
                try:
                    path = nx.shortest_path(self.G, n1, n2)
                    if len(path) > len(longest_path):
                        longest_path = path
                except nx.NetworkXNoPath:
                    pass
            if longest_path:
                self.routes.append(longest_path)
        
        # --- NEW: Create a quick-reference set of all valid BRTS stops ---
        self.brts_stops = set()
        for route in self.routes:
            self.brts_stops.update(route)
        
        for i in range(num_buses):
            assigned_route = self.routes[i % len(self.routes)]
            bus = BusAgent(f"Bus_{i}", self, route_nodes=assigned_route)
            start_node = assigned_route[0]
            self.grid.place_agent(bus, start_node)
            self.schedule.add(bus)
            
        for i in range(self.num_commuters):
            dest = self.random.choice(nodes)
            commuter = CommuterAgent(f"Commuter_{i}", self, destination=dest)
            start_node = self.random.choice(nodes)
            self.grid.place_agent(commuter, start_node)
            self.schedule.add(commuter)
            # Notice we NO LONGER force them into a queue right away. They start by 'evaluating'

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "In Bus": get_commuters_in_bus,
                "Waiting": get_commuters_waiting,
                "Lost": "commuters_lost"
            }
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()