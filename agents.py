import mesa

class CommuterAgent(mesa.Agent):
    def __init__(self, unique_id, model, destination):
        super().__init__(unique_id, model)
        self.destination = destination
        self.waiting_time = 0
        self.in_bus = False

    def step(self):
        # Rule: If not in bus, wait. If wait is too long, maybe take an auto!
        if not self.in_bus:
            self.waiting_time += 1
            if self.waiting_time > 15:
                # e.g., Commuter gives up on the bus due to high wait time
                self.model.commuters_lost += 1
                self.model.schedule.remove(self)

class BusAgent(mesa.Agent):
    def __init__(self, unique_id, model, route_nodes):
        super().__init__(unique_id, model)
        self.capacity = 50
        self.passengers = 0
        self.route = route_nodes
        self.current_stop_index = 0

    def step(self):
        # Move to the next stop on the route
        self.current_stop_index = (self.current_stop_index + 1) % len(self.route)
        next_node = self.route[self.current_stop_index]
        self.model.grid.move_agent(self, next_node)
        # (Logic to pick up waiting commuters at this node would go here)