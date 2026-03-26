import mesa
import networkx as nx

class CommuterAgent(mesa.Agent):
    def __init__(self, unique_id, model, destination):
        super().__init__(unique_id, model)
        self.destination = destination
        self.state = "waiting"
        self.waiting_time = 0
        self.patience = self.random.randint(20, 50) 

    def step(self):
        if self.state in ["arrived", "abandoned", "in_bus"]:
            return

        if self.state == "waiting":
            self.waiting_time += 1
            
            # Check Patience
            if self.waiting_time > self.patience:
                self.state = "abandoned"
                self.model.commuters_lost += 1
                
                # --- NEW: Safely remove commuter from the queue if they leave ---
                if self in self.model.stop_queues[self.pos]:
                    self.model.stop_queues[self.pos].remove(self)
                    
                self.model.grid.remove_agent(self)

class BusAgent(mesa.Agent):
    def __init__(self, unique_id, model, route_nodes):
        super().__init__(unique_id, model)
        self.capacity = 40 
        self.passengers = []
        self.target_node = self.random.choice(route_nodes)

    def step(self):
        # 1. Drop off passengers
        passengers_to_drop = [p for p in self.passengers if p.destination == self.pos]
        for p in passengers_to_drop:
            p.state = "arrived"
            self.passengers.remove(p)
            self.model.grid.place_agent(p, self.pos)

        # 2. --- NEW: Pick up from the stop's queue (FIFO) ---
        current_queue = self.model.stop_queues[self.pos]
        
        # While line isn't empty AND bus isn't full
        while len(current_queue) > 0 and len(self.passengers) < self.capacity:
            next_commuter = current_queue.pop(0) # Grab the first person in line
            next_commuter.state = "in_bus"
            self.passengers.append(next_commuter)
            self.model.grid.remove_agent(next_commuter) 

        # 3. Pathfinding
        if self.pos == self.target_node:
            nodes = list(self.model.G.nodes)
            self.target_node = self.random.choice(nodes)
            
        # 4. Move
        try:
            path = nx.shortest_path(self.model.G, source=self.pos, target=self.target_node)
            if len(path) > 1:
                next_node = path[1]
                self.model.grid.move_agent(self, next_node)
        except nx.NetworkXNoPath:
            nodes = list(self.model.G.nodes)
            self.target_node = self.random.choice(nodes)