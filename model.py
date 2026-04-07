import mesa
import networkx as nx
import osmnx as ox
import numpy as np
import math
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
        self.total_target_commuters = num_commuters
        self.commuters_lost = 0
        
        # Start at 06:00 AM (360 minutes into the day)
        self.ticks = 360 
        
        self.route_colors = [
            '#e6194b', '#3cb44b', '#ff9900', '#4363d8', '#911eb4', 
            '#46f0f0', '#f032e6', '#008080', '#e6beff', '#800000'
        ]
        
        print("Downloading Indore street data...")
        # Adjusted distance to 2.5km to ensure a dense enough graph for 10 routes
        self.G = ox.graph_from_address('Palasia Square, Indore, India', dist=1000, network_type='drive')
        self.G = nx.Graph(self.G) 
        self.G = nx.convert_node_labels_to_integers(self.G)
        self.G.graph['animate_map'] = animate_map
        
        self.grid = mesa.space.NetworkGrid(self.G)
        self.schedule = mesa.time.RandomActivation(self)
        
        self.nodes = list(self.G.nodes)
        self.stop_queues = {node: [] for node in self.nodes}

        # --- Population Density Weighting ---
        # Assume Node 0 (or closest to center) is the Commercial Hub
        self.home_weights = []
        self.work_weights = []
        
        for node in self.nodes:
            # Distance-based weighting: further = more likely Home, closer = more likely Work
            try:
                dist = nx.shortest_path_length(self.G, source=0, target=node)
            except:
                dist = 20 # Fallback for disconnected components
            
            self.home_weights.append(1.0 + (dist * 0.2))
            self.work_weights.append(1.0 / (1.0 + dist * 0.2))

        # Normalize weights so they sum to 1.0 for np.random.choice
        self.home_weights = np.array(self.home_weights) / sum(self.home_weights)
        self.work_weights = np.array(self.work_weights) / sum(self.work_weights)

        # --- Route and Stop Generation ---
        self.routes = []
        self.bus_stops = set()
        self.route_nodes_set = set()
        stop_spacing = 4 

        for r_idx in range(num_routes): 
            longest_path = []
            for _ in range(20): # Try 20 times to find a significant corridor
                n1, n2 = self.random.choice(self.nodes), self.random.choice(self.nodes)
                try:
                    path = nx.shortest_path(self.G, n1, n2)
                    if len(path) > len(longest_path):
                        longest_path = path
                except nx.NetworkXNoPath:
                    pass
            
            if len(longest_path) > 5:
                self.routes.append(longest_path)
                self.route_nodes_set.update(longest_path)
                for i, node in enumerate(longest_path):
                    if i % stop_spacing == 0 or i == len(longest_path) - 1:
                        self.bus_stops.add(node)
        
        # Tag graph for visualizer
        for node in self.G.nodes:
            self.G.nodes[node]['is_bus_stop'] = node in self.bus_stops
            self.G.nodes[node]['is_route_node'] = node in self.route_nodes_set
            
        nx.set_edge_attributes(self.G, False, "is_route")
        nx.set_edge_attributes(self.G, '#f0f0f0', "color") 
        
        for idx, route in enumerate(self.routes):
            color = self.route_colors[idx % len(self.route_colors)]
            for i in range(len(route) - 1):
                u, v = route[i], route[i+1]
                if self.G.has_edge(u, v):
                    self.G[u][v]['is_route'] = True
                    self.G[u][v]['color'] = color 
        
        # Initialize Buses
        for i in range(num_buses):
            r_idx = i % len(self.routes)
            assigned_route = self.routes[r_idx]
            bus = BusAgent(f"Bus_{i}", self, assigned_route, self.route_colors[r_idx % 10])
            bus.current_route_index = self.random.randint(0, len(assigned_route) - 1)
            self.grid.place_agent(bus, assigned_route[bus.current_route_index])
            self.schedule.add(bus)

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "In Bus": get_commuters_in_bus,
                "Waiting": get_commuters_waiting,
                "Lost": "commuters_lost",
                "Clock": lambda m: m.format_time()
            }
        )

    def format_time(self):
        """Converts simulation ticks to a 24h string."""
        total_minutes = self.ticks
        hours = (total_minutes // 60) % 24
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"

    def get_spawn_probability(self):
        """
        Bimodal distribution for Rush Hours.
        Peak 1 (Morning): 09:00 (540 mins)
        Peak 2 (Evening): 18:00 (1080 mins)
        """
        t = self.ticks % 1440
        # Morning peak Gaussian
        m_peak = 540
        m_std = 60
        morning = math.exp(-(t - m_peak)**2 / (2 * m_std**2))
        
        # Evening peak Gaussian
        e_peak = 1080
        e_std = 90
        evening = math.exp(-(t - e_peak)**2 / (2 * e_std**2))
        
        # Base probability + peak surges
        return 0.02 + (morning * 0.4) + (evening * 0.3)

    def step(self):
        self.ticks += 1
        
        # Logic for spreading commuters throughout the day
        # We spawn agents until we hit the target population
        current_commuters = sum(1 for a in self.schedule.agents if type(a).__name__ == "CommuterAgent")
        
        if current_commuters < self.total_target_commuters:
            if self.random.random() < self.get_spawn_probability():
                # Weighted selection for Home and Work
                h_node = int(np.random.choice(self.nodes, p=self.home_weights))
                w_node = int(np.random.choice(self.nodes, p=self.work_weights))
                
                # Prevent Home and Work being the same node
                if h_node != w_node:
                    c_id = f"Commuter_{self.ticks}_{current_commuters}"
                    commuter = CommuterAgent(c_id, self, h_node, w_node)
                    self.grid.place_agent(commuter, h_node)
                    self.schedule.add(commuter)

        self.datacollector.collect(self)
        self.schedule.step()