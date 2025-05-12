from flask import Flask, render_template, jsonify, request
import networkx as nx
import random
import matplotlib.pyplot as plt
import io
import base64
from typing import List, Dict, Optional, Tuple

app = Flask(__name__)

# Constants
NODE_TYPES = {
    "Building": ["A Building", "B Building", "E Building", "F Building", "I Building", "J Building"],
    "Junction": ["C Junction", "G Junction", "K Junction"],
    "Enemy Camp": ["D Enemy Camp", "H Enemy Camp"],
    "Home": ["Home Node"]
}

ROLES = ["Army", "Volunteer", "Rescuer"]
MIN_CONNECTIONS = 2
MAX_CONNECTIONS = 3
MIN_COST = 1
MAX_COST = 10

class PerfectPathway:
    def __init__(self):
        self.G: Optional[nx.Graph] = None
        self.home_node = "Home Node"
        self.destination_node: Optional[str] = None
        self.selected_role: Optional[str] = None

    def get_node_connections(self, node: str, edges: List[Tuple[str, str]]) -> int:
        """Get the number of connections for a given node."""
        return sum(1 for edge in edges if node in edge)

    def generate_random_connections(self) -> List[Tuple[str, str]]:
        """Generate random connections between nodes ensuring the graph is connected."""
        all_nodes = [node for nodes in NODE_TYPES.values() for node in nodes]
        edges = []
        connected_nodes = {self.home_node}
        
        unconnected_nodes = set(all_nodes) - connected_nodes
        while unconnected_nodes:
            node = random.choice(list(unconnected_nodes))
            available_connected = [n for n in connected_nodes 
                                if self.get_node_connections(n, edges) < MAX_CONNECTIONS]
            if not available_connected:
                return self.generate_random_connections()
            connected_to = random.choice(available_connected)
            edges.append((connected_to, node))
            connected_nodes.add(node)
            unconnected_nodes.remove(node)
        
        for node in all_nodes:
            current_connections = self.get_node_connections(node, edges)
            if current_connections < MIN_CONNECTIONS:
                attempts = 0
                while current_connections < MIN_CONNECTIONS and attempts < 100:
                    other_node = random.choice(all_nodes)
                    if (other_node != node and 
                        self.get_node_connections(other_node, edges) < MAX_CONNECTIONS and
                        (node, other_node) not in edges and 
                        (other_node, node) not in edges):
                        edges.append((node, other_node))
                        current_connections += 1
                    attempts += 1
                
                if current_connections < MIN_CONNECTIONS:
                    return self.generate_random_connections()
        
        return edges

    def initialize_graph(self):
        try:
            self.G = nx.Graph()
            all_nodes = [node for nodes in NODE_TYPES.values() for node in nodes]
            self.G.add_nodes_from(all_nodes)
            
            edges = self.generate_random_connections()
            
            for edge in edges:
                self.G.add_edge(edge[0], edge[1], cost=random.randint(MIN_COST, MAX_COST))
                
            if not nx.is_connected(self.G):
                self.initialize_graph()
                return
                
            return True
        except Exception as e:
            return False

    def find_path(self, role: str, destination: str) -> Dict:
        try:
            self.selected_role = role
            self.destination_node = destination
            
            if not self.G:
                self.initialize_graph()
            
            path = nx.shortest_path(self.G, source=self.home_node,
                                  target=self.destination_node, weight='cost')
            
            total_cost = sum(self.G[path[i]][path[i+1]]['cost'] 
                           for i in range(len(path)-1))
            
            # Create visualization
            plt.figure(figsize=(12, 8))
            pos = nx.spring_layout(self.G, k=1, iterations=50)
            
            # Draw all nodes
            nx.draw_networkx_nodes(self.G, pos, node_color='lightgray',
                                 node_size=700)
            
            # Draw all edges in gray with their costs
            nx.draw_networkx_edges(self.G, pos, edge_color='gray', width=1)
            
            # Draw the selected path in blue with thicker lines
            path_edges = [(path[i], path[i+1]) for i in range(len(path)-1)]
            nx.draw_networkx_edges(self.G, pos, edgelist=path_edges,
                                 edge_color='blue', width=3)
            
            # Draw all node labels
            nx.draw_networkx_labels(self.G, pos, font_weight='bold')
            
            # Draw edge labels for all edges
            edge_labels = {(u, v): d['cost'] for u, v, d in self.G.edges(data=True)}
            nx.draw_networkx_edge_labels(self.G, pos, edge_labels=edge_labels,
                                       font_color='red', font_size=8)
            
            plt.title(f"Perfect Pathway - {self.selected_role}'s Route\n"
                     f"Selected path shown in blue, costs shown in red")
            plt.axis('off')
            
            # Convert plot to base64 string
            img = io.BytesIO()
            plt.savefig(img, format='png', bbox_inches='tight')
            img.seek(0)
            plot_url = base64.b64encode(img.getvalue()).decode()
            plt.close()
            
            return {
                'success': True,
                'path': path,
                'total_cost': total_cost,
                'plot_url': plot_url
            }
            
        except nx.NetworkXNoPath:
            return {'success': False, 'error': 'No valid path found to the destination!'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Initialize the pathway
pathway = PerfectPathway()

@app.route('/')
def index():
    return render_template('index.html', 
                         roles=ROLES,
                         node_types=NODE_TYPES)

@app.route('/simulate', methods=['POST'])
def simulate():
    data = request.get_json()
    role = data.get('role')
    destination = data.get('destination')
    
    if not role or not destination:
        return jsonify({'success': False, 'error': 'Missing role or destination'})
    
    result = pathway.find_path(role, destination)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True) 