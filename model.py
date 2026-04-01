import mesa
import networkx as nx
import osmnx as ox
from agents import CommuterAgent, BusAgent

def get_commuters_in_bus(model):
    return sum(1 for a in model.schedule.agents 
               if type(a).__name__ == "CommuterAgent" and a.state == "in_bus")

def get_commuters_waiting(model):
    return sum(1 for a in model.schedule.agents 
               if type(a).__name__ == "CommuterAgent" and a.state in ["waiting", "walking_to_stop", "evaluating"])

class IndoreTransitModel(mesa.Model):
    def __init__(self, num_commuters, num_buses, num_routes, animate_map=True):
        super().__init__()
        self.num_commuters = num_commuters
        self.commuters_lost = 0
        
        self.route_colors = [
            '#e6194b', '#3cb44b', '#ff9900', '#4363d8', '#911eb4', 
            '#46f0f0', '#f032e6', '#008080', '#e6beff', '#800000'
        ]
        
        print("Downloading Indore street data...")
        self.G = ox.graph_from_address('Palasia Square, Indore, India', dist=1000, network_type='drive')
        self.G = nx.Graph(self.G) 
        self.G = nx.convert_node_labels_to_integers(self.G)
        
        self.G.graph['animate_map'] = animate_map
        
        self.grid = mesa.space.NetworkGrid(self.G)
        self.schedule = mesa.time.RandomActivation(self)
        
        nodes = list(self.G.nodes)
        self.stop_queues = {node: [] for node in nodes}
        
        self.routes = []
        for _ in range(num_routes): 
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
        
        # --- NEW: Space out the bus stops ---
        self.bus_stops = set()
        self.route_nodes_set = set()
        stop_spacing = 4 # Only make every 4th intersection a bus stop
        
        for route in self.routes:
            self.route_nodes_set.update(route)
            for i, node in enumerate(route):
                # Always make the first and last node a stop, plus the intervals
                if i % stop_spacing == 0 or i == len(route) - 1:
                    self.bus_stops.add(node)
            
        for node in self.G.nodes:
            self.G.nodes[node]['is_bus_stop'] = node in self.bus_stops
            self.G.nodes[node]['is_route_node'] = node in self.route_nodes_set
            
        nx.set_edge_attributes(self.G, False, "is_route")
        nx.set_edge_attributes(self.G, '#f0f0f0', "color") 
        
        for idx, route in enumerate(self.routes):
            route_color = self.route_colors[idx % len(self.route_colors)]
            for i in range(len(route) - 1):
                u, v = route[i], route[i+1]
                if self.G.has_edge(u, v):
                    self.G[u][v]['is_route'] = True
                    self.G[u][v]['color'] = route_color 
        
        for i in range(num_buses):
            route_idx = i % len(self.routes)
            assigned_route = self.routes[route_idx]
            route_color = self.route_colors[route_idx % len(self.route_colors)]
            
            start_index = self.random.randint(0, len(assigned_route) - 1)
            
            bus = BusAgent(f"Bus_{i}", self, route_nodes=assigned_route, color=route_color)
            bus.current_route_index = start_index 
            
            start_node = assigned_route[start_index]
            self.grid.place_agent(bus, start_node)
            self.schedule.add(bus)
            
        for i in range(self.num_commuters):
            commuter = CommuterAgent(f"Commuter_{i}", self)
            self.grid.place_agent(commuter, commuter.home_node)
            self.schedule.add(commuter)

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