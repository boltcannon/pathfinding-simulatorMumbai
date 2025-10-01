import os
import osmnx as ox
import networkx as nx
from flask import Flask, request, jsonify

app = Flask(__name__)

GRAPH_FILE = os.path.join(os.path.dirname(__file__), "mumbai.graphml")

def load_graph():
    """
    Load Mumbai road network.
    If graphml file exists, load it.
    If not, download and save it for future use.
    """
    if os.path.exists(GRAPH_FILE):
        print(f"Loading graph from {GRAPH_FILE} ...")
        return ox.load_graphml(GRAPH_FILE)
    else:
        print("Graph file not found, downloading from OSM...")
        G = ox.graph_from_place("Mumbai, India", network_type="drive")
        ox.save_graphml(G, GRAPH_FILE)
        print("Graph downloaded and saved.")
        return G

# Global graph object
try:
    G = load_graph()
except Exception as e:
    print(f"❌ Could not load graph: {e}")
    G = None

@app.route("/api/compare_routes")
def compare_routes():
    if G is None:
        return jsonify({"error": "Graph could not be loaded"}), 500

    start = request.args.get("start")
    end = request.args.get("end")

    if not start or not end:
        return jsonify({"error": "Missing start or end parameter"}), 400

    try:
        print(f"Geocoding '{start}' and '{end}' within Mumbai...")
        start_point = ox.geocode(start + ", Mumbai, India")
        end_point = ox.geocode(end + ", Mumbai, India")

        # Nearest graph nodes
        start_node = ox.distance.nearest_nodes(G, start_point[1], start_point[0])
        end_node = ox.distance.nearest_nodes(G, end_point[1], end_point[0])

        # Example: shortest path (Dijkstra for now)
        path = nx.shortest_path(G, source=start_node, target=end_node, weight="length")
        path_coords = [(G.nodes[n]["y"], G.nodes[n]["x"]) for n in path]

        return jsonify({
            "results": [
                {"algo": "Dijkstra", "distance": round(nx.shortest_path_length(G, start_node, end_node, weight="length")/1000, 2),
                 "time": 0, "visited": len(path)}
            ],
            "fastest_algo": "Dijkstra",
            "animation_data": {
                "path_coords": path_coords,
                "visited_coords": path_coords
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
