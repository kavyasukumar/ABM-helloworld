import os
import tornado.web
import json
from mesa.visualization.modules import NetworkModule
from mesa.visualization.ModularVisualization import ModularServer, VisualizationElement
from mesa.visualization.UserParam import Slider, Checkbox 
from model import IndoreTransitModel

CANVAS_WIDTH = 600
CANVAS_HEIGHT = 600
PADDING = 30 

def network_portrayal(G):
    portrayal = dict()
    portrayal['edges'] = []
    
    base_nodes = []
    queue_nodes = []
    bus_nodes = []
    
    nodes_data = list(G.nodes(data=True))
    if not nodes_data:
        return portrayal

    xs = [data.get('x', 0) for _, data in nodes_data]
    ys = [data.get('y', 0) for _, data in nodes_data]
    
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    x_range = max_x - min_x if max_x - min_x > 0 else 1
    y_range = max_y - min_y if max_y - min_y > 0 else 1
    max_range = max(x_range, y_range) 
    
    canvas_size = CANVAS_WIDTH - (2 * PADDING)
    x_offset = PADDING + (canvas_size - (x_range / max_range) * canvas_size) / 2
    y_offset = PADDING + (canvas_size - (y_range / max_range) * canvas_size) / 2

    raw_positions = []
    for node_id, data in nodes_data:
        sx = ((data.get('x', 0) - min_x) / max_range) * canvas_size + x_offset
        sy = ((max_y - data.get('y', 0)) / max_range) * canvas_size + y_offset
        raw_positions.append((node_id, data, sx, sy))

    mean_x = sum(sx for _, _, sx, _ in raw_positions) / len(raw_positions)
    mean_y = sum(sy for _, _, _, sy in raw_positions) / len(raw_positions)

    shift_x = (CANVAS_WIDTH / 2) - mean_x
    shift_y = (CANVAS_HEIGHT / 2) - mean_y

    animate_map = G.graph.get('animate_map', True)

    for node_id, node_data, sx, sy in raw_positions:
        final_x = sx + shift_x
        final_y = sy + shift_y
        
        is_route_node = node_data.get('is_route_node', False)
        is_bus_stop = node_data.get('is_bus_stop', False)
        
        # Keep inactive stops completely invisible
        if is_route_node:
            base_nodes.append({
                'id': node_id, 
                'size': 4 if is_bus_stop else 1.5,
                'color': '#666666' if is_bus_stop else '#cccccc',
                'x': final_x, 'y': final_y, 'fx': final_x, 'fy': final_y, 
                'tooltip': f"Bus Stop {node_id}" if is_bus_stop else f"Waypoint {node_id}"
            })
        else:
            base_nodes.append({
                'id': node_id, 
                'size': 0.001, 
                'color': 'rgba(0,0,0,0)', 
                'x': final_x, 'y': final_y, 'fx': final_x, 'fy': final_y, 
                'tooltip': ""
            })
        
        if animate_map:
            agents = node_data.get('agent', [])
            
            waiting_commuters = [a for a in agents if type(a).__name__ == "CommuterAgent" and a.state in ["waiting", "walking_to_stop", "evaluating"]]
            queue_size = len(waiting_commuters)
            if queue_size > 0:
                queue_nodes.append({
                    'id': f"queue_{node_id}", 
                    'size': min(6 + (queue_size * 2), 14),
                    'color': '#0000ff',
                    'x': final_x, 'y': final_y, 'fx': final_x, 'fy': final_y, 
                    'tooltip': f"Queue/Walking: {queue_size}"
                })
                
            buses = [a for a in agents if type(a).__name__ == "BusAgent"]
            if buses:
                bus = buses[0] 
                fill_ratio = len(bus.passengers) / bus.capacity
                bus_nodes.append({
                    'id': f"bus_{node_id}_{bus.unique_id}", 
                    'size': 10 + (fill_ratio * 8),
                    'color': bus.color,
                    'x': final_x, 'y': final_y, 'fx': final_x, 'fy': final_y, 
                    'tooltip': f"🚌 Bus: {len(bus.passengers)}/{bus.capacity}"
                })
        
    portrayal['nodes'] = base_nodes + queue_nodes + bus_nodes
        
    for source, target, edge_data in G.edges(data=True):
        is_route = edge_data.get('is_route', False)
        
        if is_route:
            portrayal['edges'].append({
                'source': source, 
                'target': target, 
                'color': edge_data.get('color', '#333333'),
                'width': 4 
            })
        else:
            # --- UPDATED: Draw inactive roads as faint background lines ---
            portrayal['edges'].append({
                'source': source, 
                'target': target, 
                'color': '#eeeeee', 
                'width': 1 
            })
        
    return portrayal

network = NetworkModule(network_portrayal, CANVAS_WIDTH, CANVAS_HEIGHT)

class StackedAreaChart(VisualizationElement):
    # --- STEP 1: Empty this out so Mesa doesn't create a broken local link ---
    package_includes = [] 
    local_includes = ["StackedAreaChartModule.js"] 

    def __init__(self, series, canvas_height=250, canvas_width=600, data_collector_name="datacollector"):
        self.series = series
        self.canvas_height = canvas_height
        self.canvas_width = canvas_width
        self.data_collector_name = data_collector_name
        
        series_json = json.dumps(self.series)
        
        # --- STEP 2: Manually inject the script tag into the HTML head ---
        # This bypasses Mesa's path-prepending logic entirely.
        self.js_code = f"""
        (function() {{
            if (!document.getElementById('chart-js-cdn')) {{
                var script = document.createElement('script');
                script.id = 'chart-js-cdn';
                script.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/2.9.4/Chart.min.js';
                document.head.appendChild(script);
            }}
            // Now initialize your custom module
            window.myChart = new StackedAreaChartModule({series_json}, {self.canvas_width}, {self.canvas_height});
        }})();
        """

    def render(self, model):
        current_values = []
        data_collector = getattr(model, self.data_collector_name)
        for s in self.series:
            name = s["Label"]
            try:
                val = data_collector.model_vars[name][-1]
            except (IndexError, KeyError):
                val = 0
            current_values.append(val)
        return current_values

combined_chart = StackedAreaChart([
    {"Label": "Waiting", "Color": "rgba(31, 119, 180, 0.7)"},   
    {"Label": "In Bus", "Color": "rgba(44, 160, 44, 0.7)"},     
    {"Label": "Lost", "Color": "rgba(214, 39, 40, 0.7)"}        
])

model_params = {
    "num_commuters": Slider(
        "Total Commuters", value=100, min_value=10, max_value=1000, step=10, 
        description="Total number of commuters in Indore"
    ),
    "num_buses": Slider(
        "Buses", value=5, min_value=1, max_value=50, step=1, 
        description="Number of buses operating on the corridor"
    ),
    "num_routes": Slider(
        "Bus Routes", value=4, min_value=1, max_value=10, step=1, 
        description="Number of distinct bus routes crossing the city"
    ),
    "animate_map": Checkbox("Animate Map Agents (CPU Saver)", value=True)
}

server = ModularServer(IndoreTransitModel,
                       [network, combined_chart],
                       "Indore Bus Ridership Model",
                       model_params)

# Get the absolute path to your current directory
current_path = os.path.dirname(os.path.realpath(__file__))

# Create a custom handler to serve your JS file
class JSHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        self.set_header("Cache-Control", "no-cache, no-store, must-revalidate")

# Define the server
server = ModularServer(IndoreTransitModel,
                       [network, combined_chart],
                       "Indore Bus Ridership Model",
                       model_params)

# Manually add the route so the browser can find your JS file
server.handlers.append((r"/(StackedAreaChartModule.js)", JSHandler, {"path": current_path}))

server.port = 8521 
server.launch()