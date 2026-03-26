# --- NEW: Import ChartModule ---
from mesa.visualization.modules import NetworkModule, ChartModule
from mesa.visualization.ModularVisualization import ModularServer
from model import IndoreTransitModel

def network_portrayal(G):
    portrayal = dict()
    portrayal['nodes'] = []
    portrayal['edges'] = []
    
    xs = [data.get('x', 0) for _, data in G.nodes(data=True)]
    ys = [data.get('y', 0) for _, data in G.nodes(data=True)]
    
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    for node_id, node_data in G.nodes(data=True):
        color = '#cccccc' 
        size = 2 
        tooltip_text = f"Stop {node_id}"
        
        agents = node_data.get('agent', [])
        
        waiting_commuters = [a for a in agents if type(a).__name__ == "CommuterAgent" and a.state == "waiting"]
        queue_size = len(waiting_commuters)
        
        if queue_size > 0:
            color = '#0000ff' 
            size = min(3 + queue_size, 8) 
            tooltip_text += f" | Queue: {queue_size}"
            
        buses = [a for a in agents if type(a).__name__ == "BusAgent"]
        
        if buses:
            bus = buses[0] 
            color = '#ff0000' 
            fill_ratio = len(bus.passengers) / bus.capacity
            size = 5 + (fill_ratio * 5) 
            tooltip_text += f" | 🚌 Bus: {len(bus.passengers)}/{bus.capacity}"
        
        x_range = (max_x - min_x) if (max_x - min_x) > 0 else 1
        y_range = (max_y - min_y) if (max_y - min_y) > 0 else 1
        
        scaled_x = ((node_data.get('x', 0) - min_x) / x_range) * 460 + 20
        scaled_y = ((node_data.get('y', 0) - min_y) / y_range) * 460 + 20
        
        portrayal['nodes'].append({
            'id': node_id, 
            'size': size,
            'color': color,
            'x': scaled_x,
            'y': -scaled_y,
            'tooltip': tooltip_text,
            'label': tooltip_text
        })
        
    for source, target in G.edges():
        portrayal['edges'].append({
            'source': source, 
            'target': target, 
            'color': '#000000',
            'width': 4
        })
        
    return portrayal

network = NetworkModule(network_portrayal, 500, 500)

# --- NEW: Create the Chart Modules ---
chart_ridership = ChartModule([{"Label": "Total Ridership", "Color": "#2ca02c"}]) # Green
chart_utilization = ChartModule([{"Label": "Avg Capacity Utilization (%)", "Color": "#1f77b4"}]) # Blue
chart_lost = ChartModule([{"Label": "Lost Riders", "Color": "#d62728"}]) # Red

# --- NEW: A single combined ChartModule ---
combined_chart = ChartModule([
    {"Label": "Waiting", "Color": "#1f77b4"},   # Blue line for waiting in queue
    {"Label": "In Bus", "Color": "#2ca02c"},    # Green line for riding
    {"Label": "Lost Riders", "Color": "#d62728"}       # Red line for abandoned
])

# --- UPDATED: Add charts to the server ---
server = ModularServer(IndoreTransitModel,
                       [network, combined_chart, chart_ridership, chart_utilization, chart_lost],
                       "Indore Bus Ridership Model",
                       {"num_commuters": 100, "num_buses": 5})

server.port = 8521 
server.launch()