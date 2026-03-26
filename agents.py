import mesa
import networkx as nx

class CommuterAgent(mesa.Agent):
    def __init__(self, unique_id, model, destination):
        super().__init__(unique_id, model)
        self.destination = destination
        self.state = "waiting" 
        self.waiting_time = 0
        self.patience = self.random.randint(20, 50) 
        self.activity_time = 0 

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
                
                self.state = "waiting"
                self.waiting_time = 0
                self.patience = self.random.randint(20, 50)
                
                self.model.stop_queues[self.pos].append(self)
            return

        if self.state == "waiting":
            self.waiting_time += 1
            
            if self.waiting_time > self.patience:
                self.model.commuters_lost += 1
                
                if self in self.model.stop_queues[self.pos]:
                    self.model.stop_queues[self.pos].remove(self)
                    
                self.model.grid.remove_agent(self)
                
                self.model.grid.place_agent(self, self.destination)
                self.state = "activity"
                self.activity_time = self.random.randint(50, 200)

class BusAgent(mesa.Agent):
    def __init__(self, unique_id, model, route_nodes):
        super().__init__(unique_id, model)
        self.capacity = 40 
        self.passengers = []
        
        # --- NEW: Fixed Route Properties ---
        self.route = route_nodes      # The strict list of nodes to follow
        self.current_route_index = 0  # Where the bus currently is on the route
        self.direction = 1            # 1 for forward, -1 for return trip

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

        # 3. --- NEW: Strict Route Movement ---
        if len(self.route) > 1:
            # Calculate the next index
            next_index = self.current_route_index + self.direction

            # If we hit the end of the line (or the beginning), reverse direction!
            if next_index >= len(self.route) or next_index < 0:
                self.direction *= -1 
                next_index = self.current_route_index + self.direction

            # Move to the next node on the predefined route
            self.current_route_index = next_index
            next_node = self.route[self.current_route_index]
            self.model.grid.move_agent(self, next_node)