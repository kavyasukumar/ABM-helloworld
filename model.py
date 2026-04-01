import mesa
import networkx as nx
import osmnx as ox
import numpy as np
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
        self.route_colors = ['#e6194b', '#3cb44b', '#ff9900', '#4363d8', '#911eb4', '#46f0f0', '#f032e6', '#008080', '#e6beff', '#800000']
        
        print("Downloading Indore street data...")
        self.G = ox.graph_from_address('Palasia Square, Indore, India', dist=1000, network_type='drive')
        self.G = nx.Graph(self.G) 
        self.G = nx.convert_node_labels_to_integers(self.G)
        self.G.graph['animate_map'] = animate_map
        
        self.grid = mesa.space.NetworkGrid(self.G)
        self.schedule = mesa.time.RandomActivation(self)
        
        nodes = list(self.G.nodes)
        self.stop_queues = {node: [] for node in nodes}

        # --- NEW: Density Weighting Logic ---
        self.home_weights = []
        self.work_weights = []
        
        # We assume the center of our graph (Palasia) is highly commercial
        # Nodes further away are more likely to be residential
        center_node = 0 
        for node in nodes:
            dist = nx.shortest_path_length(self.G, source=center_node, target=node) if nx.has_path(self.G, center_node, node) else 50
            
            # Home weight: Higher for peripheral/dense residential zones
            h_w = 1.0 + (dist * 0.1) 
            # Work weight: Higher for central/commercial zones
            w_w = 1.0 / (1.0 + dist * 0.1)
            
            self.home_weights.append(h_w)
            self.work_weights.append(w_w)

        # Normalize weights
        self.home_weights = np.array(self.home_weights) / sum(self.home_weights)
        self.work_weights = np.array(self.work_weights) / sum(self.work_weights)

        # Route Generation
        self.routes = []
        for _ in range(num_routes): 
            longest_path = []
            for _ in range(15):
                n1, n2 = self.random.choice(nodes), self.random.choice(nodes)
                try:
                    path = nx.shortest_path(self.G, n1, n2)
                    if len(path) > len(longest_path): longest_path = path
                except nx.NetworkXNoPath: pass
            if longest_path: self.routes.append(longest_path)
        
        self.bus_stops = set()
        self.route_nodes_set = set()
        stop_spacing = 4 
        for route in self.routes:
            self.route_nodes_set.update(route)
            for i, node in enumerate(route):
                if i % stop_spacing == 0 or i == len(route) - 1: self.bus_stops.add(node)
            
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
            bus = BusAgent(f"Bus_{i}", self, route_nodes=assigned_route, color=self.route_colors[route_idx % 10])
            bus.current_route_index = self.random.randint(0, len(assigned_route) - 1)
            self.grid.place_agent(bus, assigned_route[bus.current_route_index])
            self.schedule.add(bus)
            
        for i in range(self.num_commuters):
            # --- NEW: Use Weighted Choices for Home/Work ---
            h_node = int(np.random.choice(nodes, p=self.home_weights))
            w_node = int(np.random.choice(nodes, p=self.work_weights))
            
            commuter = CommuterAgent(f"Commuter_{i}", self, home=h_node, work=w_node)
            self.grid.place_agent(commuter, h_node)
            self.schedule.add(commuter)

        self.datacollector = mesa.DataCollector(
            model_reporters={"In Bus": get_commuters_in_bus, "Waiting": get_commuters_waiting, "Lost": "commuters_lost"}
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()