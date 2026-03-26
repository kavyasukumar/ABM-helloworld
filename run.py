from mesa.visualization.modules import NetworkModule
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
        
        agents = node_data.get('agent', [])
        if agents:
            for agent in agents:
                if type(agent).__name__ == "BusAgent":
                    color = '#ff0000' 
                    size = 10
                    break 
                elif type(agent).__name__ == "CommuterAgent":
                    color = '#0000ff' 
                    size = 5
        
        x_range = (max_x - min_x) if (max_x - min_x) > 0 else 1
        y_range = (max_y - min_y) if (max_y - min_y) > 0 else 1
        
        scaled_x = ((node_data.get('x', 0) - min_x) / x_range) * 460 + 20
        scaled_y = ((node_data.get('y', 0) - min_y) / y_range) * 460 + 20
        
        portrayal['nodes'].append({
            'id': node_id, # Back to safe integers
            'size': size,
            'color': color,
            'x': scaled_x,
            'y': -scaled_y 
        })
        
    for source, target in G.edges():
        portrayal['edges'].append({
            'source': source, # Back to safe integers
            'target': target, # Back to safe integers
            'color': '#000000',
            'width': 4
        })
        
    return portrayal

network = NetworkModule(network_portrayal, 500, 500)

server = ModularServer(IndoreTransitModel,
                       [network],
                       "Indore Bus Ridership Model",
                       {"num_commuters": 100, "num_buses": 5})

server.port = 8521 
server.launch()