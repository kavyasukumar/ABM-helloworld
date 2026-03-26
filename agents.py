import mesa
import networkx as nx

class CommuterAgent(mesa.Agent):
    def __init__(self, unique_id, model, destination):
        super().__init__(unique_id, model)
        self.destination = destination
        self.state = "evaluating" # NEW STARTING STATE
        self.waiting_time = 0
        self.patience = self.random.randint(20, 50) 
        self.activity_time = 0 
        self.walk_path = [] # Will store the path to the bus stop

    def _take_auto(self):
        # Helper function for when they refuse to walk or lose patience
        self.model.commuters_lost += 1
        if self in self.model.stop_queues.get(self.pos, []):
            self.model.stop_queues[self.pos].remove(self)
            
        self.model.grid.move_agent(self, self.destination) # Teleport to destination
        self.state = "activity"
        self.activity_time = self.random.randint(50, 200)

    def step(self):
        if self.state == "in_bus":
            return

        if self.state == "arrived":
            self.state = "activity"
            self.activity_time = self.random.randint(50, 200) 
            return

        if self.state == "activity":
            self.activity_time -= 1
            if self.activity_time <= 0:
                nodes = list(self.model.G.nodes)
                self.destination = self.random.choice(nodes)
                self.state = "evaluating" # Time for next trip, evaluate options
            return

        # --- NEW: Decide whether to walk to the BRTS ---
        if self.state == "evaluating":
            # 1. Find all possible paths from current location
            try:
                paths = nx.single_source_shortest_path(self.model.G, self.pos)
            except nx.NetworkXNoPath:
                self._take_auto()
                return
            
            # 2. Filter for paths that lead to a BRTS stop and find the shortest one
            reachable_stops = {node: path for node, path in paths.items() if node in self.model.brts_stops}
            
            if not reachable_stops:
                self._take_auto() # No path to any BRTS stop
                return
                
            shortest_path = min(reachable_stops.values(), key=len)
            walk_distance = len(shortest_path) - 1 # Number of edges to walk
            
            # 3. Probability Formula: Max willingness to walk is ~12 intersections
            max_walk = 12
            if walk_distance == 0:
                probability_to_walk = 1.0
            elif walk_distance >= max_walk:
                probability_to_walk = 0.0
            else:
                probability_to_walk = 1.0 - (walk_distance / max_walk)
                
            # 4. Roll the dice
            if self.random.random() > probability_to_walk:
                self._take_auto() # Refused to walk that far
            else:
                self.walk_path = shortest_path[1:] # Save the route (excluding current node)
                if not self.walk_path:
                    # Already at a stop!
                    self.state = "waiting"
                    self.waiting_time = 0
                    self.model.stop_queues[self.pos].append(self)
                else:
                    self.state = "walking_to_stop"
            return

        # --- NEW: Physically walk to the stop ---
        if self.state == "walking_to_stop":
            if self.walk_path:
                next_node = self.walk_path.pop(0)
                self.model.grid.move_agent(self, next_node)
            
            # Check if arrived at the stop this step
            if not self.walk_path:
                self.state = "waiting"
                self.waiting_time = 0
                self.model.stop_queues[self.pos].append(self)
            return

        # Existing waiting logic
        if self.state == "waiting":
            self.waiting_time += 1
            if self.waiting_time > self.patience:
                self._take_auto()


class BusAgent(mesa.Agent):
    def __init__(self, unique_id, model, route_nodes):
        super().__init__(unique_id, model)
        self.capacity = 40 
        self.passengers = []
        self.route = route_nodes      
        self.current_route_index = 0  
        self.direction = 1            

    def step(self):
        # 1. Drop off passengers
        passengers_to_drop = [p for p in self.passengers if p.destination == self.pos]
        for p in passengers_to_drop:
            p.state = "arrived"
            self.passengers.remove(p)
            self.model.grid.place_agent(p, self.pos)

        # 2. Pick up from the stop's queue
        current_queue = self.model.stop_queues[self.pos]
        while len(current_queue) > 0 and len(self.passengers) < self.capacity:
            next_commuter = current_queue.pop(0) 
            next_commuter.state = "in_bus"
            self.passengers.append(next_commuter)
            self.model.grid.remove_agent(next_commuter) 

        # 3. Strict Route Movement
        if len(self.route) > 1:
            next_index = self.current_route_index + self.direction

            if next_index >= len(self.route) or next_index < 0:
                self.direction *= -1 
                next_index = self.current_route_index + self.direction

            self.current_route_index = next_index
            next_node = self.route[self.current_route_index]
            self.model.grid.move_agent(self, next_node)