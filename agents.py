import mesa
import networkx as nx

class CommuterAgent(mesa.Agent):
    def __init__(self, unique_id, model):
        super().__init__(unique_id, model)
        
        nodes = list(self.model.G.nodes)
        self.home_node = self.random.choice(nodes)
        self.work_node = self.random.choice(nodes)
        
        while self.work_node == self.home_node:
            self.work_node = self.random.choice(nodes)
            
        self.destination = self.work_node
        self.state = "evaluating" 
        self.waiting_time = 0
        self.patience = self.random.randint(20, 50) 
        self.activity_time = 0 
        self.walk_path = []
        self.alight_node = None # --- NEW: Where to get off the bus ---

    def _pick_next_destination(self):
        nodes = list(self.model.G.nodes)
        roll = self.random.random()
        
        if self.pos == self.home_node:
            self.destination = self.work_node if roll < 0.80 else self.random.choice(nodes)
        elif self.pos == self.work_node:
            self.destination = self.home_node if roll < 0.80 else self.random.choice(nodes)
        else:
            self.destination = self.home_node if roll < 0.90 else self.work_node
            
        while self.destination == self.pos:
            self.destination = self.random.choice(nodes)

    def _take_auto(self):
        self.model.commuters_lost += 1
        if self in self.model.stop_queues.get(self.pos, []):
            self.model.stop_queues[self.pos].remove(self)
            
        self.model.grid.move_agent(self, self.destination) 
        self.state = "activity"
        self.activity_time = self.random.randint(50, 200)

    def step(self):
        if self.state == "in_bus":
            return

        if self.state == "arrived":
            # --- NEW: Last-mile walk. Teleport the rest of the way to the true destination ---
            self.model.grid.move_agent(self, self.destination) 
            self.state = "activity"
            self.activity_time = self.random.randint(50, 200) 
            return

        if self.state == "activity":
            self.activity_time -= 1
            if self.activity_time <= 0:
                self._pick_next_destination()
                self.state = "evaluating" 
            return

        if self.state == "evaluating":
            try:
                paths = nx.single_source_shortest_path(self.model.G, self.pos)
            except nx.NetworkXNoPath:
                self._take_auto()
                return
            
            reachable_stops = {node: path for node, path in paths.items() if node in self.model.bus_stops}
            
            if not reachable_stops:
                self._take_auto() 
                return
                
            shortest_path = min(reachable_stops.values(), key=len)
            walk_distance = len(shortest_path) - 1 
            
            # --- NEW: Calculate the drop-off stop closest to the destination ---
            try:
                dest_paths = nx.single_source_shortest_path(self.model.G, self.destination)
                dest_reachable_stops = {n: p for n, p in dest_paths.items() if n in self.model.bus_stops}
                if dest_reachable_stops:
                    closest_to_dest = min(dest_reachable_stops.values(), key=len)
                    self.alight_node = closest_to_dest[-1] 
                else:
                    self.alight_node = self.destination
            except nx.NetworkXNoPath:
                self.alight_node = self.destination
            
            max_walk = 12
            if walk_distance == 0:
                probability_to_walk = 1.0
            elif walk_distance >= max_walk:
                probability_to_walk = 0.0
            else:
                probability_to_walk = 1.0 - (walk_distance / max_walk)
                
            if self.random.random() > probability_to_walk:
                self._take_auto() 
            else:
                self.walk_path = shortest_path[1:] 
                if not self.walk_path:
                    self.state = "waiting"
                    self.waiting_time = 0
                    self.model.stop_queues[self.pos].append(self)
                else:
                    self.state = "walking_to_stop"
            return

        if self.state == "walking_to_stop":
            if self.walk_path:
                next_node = self.walk_path.pop(0)
                self.model.grid.move_agent(self, next_node)
            
            if not self.walk_path:
                self.state = "waiting"
                self.waiting_time = 0
                self.model.stop_queues[self.pos].append(self)
            return

        if self.state == "waiting":
            self.waiting_time += 1
            if self.waiting_time > self.patience:
                self._take_auto()

class BusAgent(mesa.Agent):
    def __init__(self, unique_id, model, route_nodes, color):
        super().__init__(unique_id, model)
        self.capacity = 40 
        self.passengers = []
        self.route = route_nodes      
        self.current_route_index = 0  
        self.direction = 1            
        self.color = color 

    def step(self):
        # --- UPDATED: Drop off passengers based on their calculated alight_node ---
        passengers_to_drop = [p for p in self.passengers if p.alight_node == self.pos]
        for p in passengers_to_drop:
            p.state = "arrived"
            self.passengers.remove(p)
            self.model.grid.place_agent(p, self.pos)

        current_queue = self.model.stop_queues[self.pos]
        while len(current_queue) > 0 and len(self.passengers) < self.capacity:
            next_commuter = current_queue.pop(0) 
            next_commuter.state = "in_bus"
            self.passengers.append(next_commuter)
            self.model.grid.remove_agent(next_commuter) 

        if len(self.route) > 1:
            next_index = self.current_route_index + self.direction

            if next_index >= len(self.route) or next_index < 0:
                self.direction *= -1 
                next_index = self.current_route_index + self.direction

            self.current_route_index = next_index
            next_node = self.route[self.current_route_index]
            self.model.grid.move_agent(self, next_node)