import mesa
import networkx as nx
import osmnx as ox
from agents import CommuterAgent, BusAgent

# --- NEW: Helper functions for DataCollector ---
def get_commuters_in_bus(model):
    return sum(1 for a in model.schedule.agents 
               if type(a).__name__ == "CommuterAgent" and a.state == "in_bus")

def get_commuters_waiting(model):
    return sum(1 for a in model.schedule.agents 
               if type(a).__name__ == "CommuterAgent" and a.state == "waiting")
    
def get_total_ridership(model):
    # Count commuters who successfully boarded a bus or reached their destination
    return sum(1 for a in model.schedule.agents 
               if type(a).__name__ == "CommuterAgent" and a.state in ["in_bus", "arrived"])

def get_avg_utilization(model):
    buses = [a for a in model.schedule.agents if type(a).__name__ == "BusAgent"]
    if not buses: 
        return 0
    total_passengers = sum(len(bus.passengers) for bus in buses)
    total_capacity = sum(bus.capacity for bus in buses)
    return (total_passengers / total_capacity) * 100

class IndoreTransitModel(mesa.Model):
    def __init__(self, num_commuters, num_buses):
        super().__init__()
        self.num_commuters = num_commuters
        self.commuters_lost = 0
        
        print("Downloading Indore street data...")
        self.G = ox.graph_from_address('Palasia Square, Indore, India', dist=300, network_type='drive')
        self.G = nx.Graph(self.G) 
        self.G = nx.convert_node_labels_to_integers(self.G)
        
        self.grid = mesa.space.NetworkGrid(self.G)
        self.schedule = mesa.time.RandomActivation(self)
        
        nodes = list(self.G.nodes)
        self.stop_queues = {node: [] for node in nodes}
        
        # --- NEW: Generate predefined BRTS Routes ---
        # We will create 2 major "corridors" by finding long paths across the network
        self.routes = []
        for _ in range(2): 
            longest_path = []
            # Try a few random pairs to find a nice, long route
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
        
        # Add Buses and assign them strictly to the generated routes
        for i in range(num_buses):
            # Distribute buses evenly across our generated routes
            assigned_route = self.routes[i % len(self.routes)]
            bus = BusAgent(f"Bus_{i}", self, route_nodes=assigned_route)
            
            # Bus starts at the very beginning of its assigned route
            start_node = assigned_route[0]
            self.grid.place_agent(bus, start_node)
            self.schedule.add(bus)
            
        # Add Commuters (They still spawn everywhere, simulating the whole city)
        for i in range(self.num_commuters):
            dest = self.random.choice(nodes)
            commuter = CommuterAgent(f"Commuter_{i}", self, destination=dest)
            start_node = self.random.choice(nodes)
            self.grid.place_agent(commuter, start_node)
            self.schedule.add(commuter)
            
            self.stop_queues[start_node].append(commuter)
        # --- UPDATED: Expanded DataCollector ---
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "In Bus": get_commuters_in_bus,
                "Waiting": get_commuters_waiting,
                "Lost Riders": "commuters_lost",
                "Total Ridership": get_total_ridership,
                "Avg Capacity Utilization (%)": get_avg_utilization
            }
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()