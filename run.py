from mesa.visualization.modules import NetworkModule
from mesa.visualization.ModularVisualization import ModularServer
from model import IndoreTransitModel

def network_portrayal(G):
    # The visualization needs explicit IDs, coordinates, and edge connections
    portrayal = dict()
    portrayal['nodes'] = []
    portrayal['edges'] = []
    
    for node_id, node_data in G.nodes(data=True):
        # Default intersection (node) appearance
        color = '#cccccc' # Light gray
        size = 1
        
        # Check if any agents are at this intersection
        agents = node_data.get('agent', [])
        if agents:
            for agent in agents:
                if type(agent).__name__ == "BusAgent":
                    color = '#ff0000' # RED for buses
                    size = 5
                    break # Bus takes visual priority over commuters
                elif type(agent).__name__ == "CommuterAgent":
                    color = '#0000ff' # BLUE for commuters
                    size = 3
        
        portrayal['nodes'].append({
            'id': node_id,
            'size': size,
            'color': color,
            # OSMnx uses 'x' for longitude and 'y' for latitude
            'x': node_data.get('x', 0), 
            'y': -node_data.get('y', 0) # Invert Y so North is at the top of your screen
        })
        
    for source, target in G.edges():
        portrayal['edges'].append({
            'source': source,
            'target': target,
            'color': '#e0e0e0',
            'width': 1
        })
        
    return portrayal

# Set up the visual layout (500x500 pixels)
network = NetworkModule(network_portrayal, 500, 500)

server = ModularServer(IndoreTransitModel,
                       [network],
                       "Indore Bus Ridership Model",
                       {"num_commuters": 100, "num_buses": 5})

server.port = 8521 
server.launch()