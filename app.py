from flask import Flask, render_template, jsonify, request
import osmnx as ox
import networkx as nx
import time
import heapq
import collections

# Initialize Flask App
app = Flask(__name__)

# --- Global graph for cached Mumbai map ---
GRAPH = None

def load_graph():
    """Loads the Mumbai map graph from a file for fast local queries."""
    global GRAPH
    graph_file = "mumbai.graphml"
    if GRAPH is None:
        try:
            print(f"--- Loading cached Mumbai map from {graph_file}... ---")
            GRAPH = ox.load_graphml(graph_file)
            print("--- Mumbai map data loaded successfully from file. ---")
        except FileNotFoundError:
            place = "Mumbai, Maharashtra, India"
            print(f"--- Map file not found. Downloading data for {place}... ---")
            GRAPH = ox.graph_from_place(place, network_type='drive')
            ox.save_graphml(GRAPH, filepath=graph_file)
            print(f"--- Map data downloaded and saved to {graph_file}. ---")

# --- Helper and Algorithm Functions ---
def reconstruct_path(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    return path[::-1]

def calculate_path_distance(graph, path):
    return sum(ox.distance.great_circle(graph.nodes[u]['y'], graph.nodes[u]['x'], graph.nodes[v]['y'], graph.nodes[v]['x']) for u, v in zip(path[:-1], path[1:]))

def a_star_solve(graph, start_node, end_node):
    def heuristic(u, v): return ox.distance.great_circle(graph.nodes[u]['y'], graph.nodes[u]['x'], graph.nodes[v]['y'], graph.nodes[v]['x'])
    pq = [(heuristic(start_node, end_node), start_node)]; g_scores = {start_node: 0}; came_from = {}; visited_nodes = []
    while pq:
        _, current = heapq.heappop(pq)
        if current in visited_nodes: continue
        visited_nodes.append(current)
        if current == end_node:
            path = reconstruct_path(came_from, current); dist = calculate_path_distance(graph, path)
            return path, dist, visited_nodes
        for neighbor in graph.neighbors(current):
            tentative_g_score = g_scores.get(current, float('inf')) + graph.edges[current, neighbor, 0].get('length', 1)
            if tentative_g_score < g_scores.get(neighbor, float('inf')):
                came_from[neighbor] = current; g_scores[neighbor] = tentative_g_score
                f_score = tentative_g_score + heuristic(neighbor, end_node); heapq.heappush(pq, (f_score, neighbor))
    return [], 0, visited_nodes

def dijkstra_solve(graph, start_node, end_node):
    pq = [(0, start_node)]; came_from = {}; distances = {start_node: 0}; visited_nodes = []
    while pq:
        dist, current = heapq.heappop(pq)
        if dist > distances.get(current, float('inf')): continue
        visited_nodes.append(current)
        if current == end_node:
            path = reconstruct_path(came_from, current); dist = calculate_path_distance(graph, path)
            return path, dist, visited_nodes
        for neighbor in graph.neighbors(current):
            new_dist = dist + graph.edges[current, neighbor, 0].get('length', 1)
            if new_dist < distances.get(neighbor, float('inf')):
                came_from[neighbor] = current; distances[neighbor] = new_dist; heapq.heappush(pq, (new_dist, neighbor))
    return [], 0, visited_nodes

def bfs_solve(graph, start_node, end_node):
    queue = collections.deque([start_node]); visited = {start_node}; came_from = {}; visited_nodes_in_order = []
    while queue:
        current = queue.popleft()
        visited_nodes_in_order.append(current)
        if current == end_node:
            path = reconstruct_path(came_from, current); dist = calculate_path_distance(graph, path)
            return path, dist, visited_nodes_in_order
        for neighbor in graph.neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor); came_from[neighbor] = current; queue.append(neighbor)
    return [], 0, visited_nodes_in_order

def dfs_solve(graph, start_node, end_node):
    stack = [start_node]; visited = set(); came_from = {}; visited_nodes_in_order = []
    while stack:
        current = stack.pop()
        if current in visited: continue
        visited.add(current)
        visited_nodes_in_order.append(current)
        if current == end_node:
            path = reconstruct_path(came_from, current); dist = calculate_path_distance(graph, path)
            return path, dist, visited_nodes_in_order
        for neighbor in reversed(list(graph.neighbors(current))):
            if neighbor not in visited:
                came_from[neighbor] = current; stack.append(neighbor)
    return [], 0, visited_nodes_in_order

def greedy_bfs_solve(graph, start_node, end_node):
    def heuristic(u, v): return ox.distance.great_circle(graph.nodes[u]['y'], graph.nodes[u]['x'], graph.nodes[v]['y'], graph.nodes[v]['x'])
    pq = [(heuristic(start_node, end_node), start_node)]; came_from = {}; visited = {start_node}; visited_nodes_in_order = []
    while pq:
        _, current = heapq.heappop(pq)
        if current in visited_nodes_in_order: continue
        visited_nodes_in_order.append(current)
        if current == end_node:
            path = reconstruct_path(came_from, current); dist = calculate_path_distance(graph, path)
            return path, dist, visited_nodes_in_order
        for neighbor in graph.neighbors(current):
            if neighbor not in visited:
                visited.add(neighbor); came_from[neighbor] = current
                priority = heuristic(neighbor, end_node); heapq.heappush(pq, (priority, neighbor))
    return [], 0, visited_nodes_in_order

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/compare_routes')
def compare_routes():
    start_query = request.args.get('start', 'IIT Bombay')
    end_query = request.args.get('end', 'Bandra Fort')
    
    try:
        # --- SIMPLIFIED LOGIC: ALWAYS USE THE CACHED MUMBAI GRAPH ---
        print(f"--- Geocoding '{start_query}' and '{end_query}' within Mumbai... ---")
        start_coords = ox.geocode(f"{start_query}, Mumbai, India")
        end_coords = ox.geocode(f"{end_query}, Mumbai, India")
        
        # Use the pre-loaded GRAPH object for all calculations
        local_graph = GRAPH
        
        start_node = ox.distance.nearest_nodes(local_graph, start_coords[1], start_coords[0])
        end_node = ox.distance.nearest_nodes(local_graph, end_coords[1], end_coords[0])
        
        solvers = {
            'A* (A-Star)': a_star_solve, 'Dijkstra': dijkstra_solve,
            'Greedy BFS': greedy_bfs_solve, 'BFS': bfs_solve, 'DFS': dfs_solve
        }
        
        results, best_path, min_distance, animation_visited_nodes = [], [], float('inf'), []
        for name, solver_func in solvers.items():
            start_time = time.time()
            path, distance, visited_nodes = solver_func(local_graph, start_node, end_node)
            end_time = time.time()
            if path:
                results.append({'algo': name, 'distance': round(distance / 1000, 2), 'time': round((end_time - start_time) * 1000, 2), 'visited': len(visited_nodes)})
                if name in ['A* (A-Star)', 'Dijkstra', 'BFS'] and distance < min_distance and distance > 0:
                    min_distance, best_path, animation_visited_nodes = distance, path, visited_nodes
        
        fastest_algo_name = min(results, key=lambda x: x['time'])['algo'] if results else None
        
        animation_data = {}
        if best_path:
            nodes = local_graph.nodes(data=True)
            min_lon = min(d['x'] for _, d in nodes); max_lon = max(d['x'] for _, d in nodes)
            min_lat = min(d['y'] for _, d in nodes); max_lat = max(d['y'] for _, d in nodes)
            
            animation_data = {
                'bounds': [[min_lon, max_lon], [min_lat, max_lat]],
                'visited_coords': [[local_graph.nodes[node]['y'], local_graph.nodes[node]['x']] for node in animation_visited_nodes],
                'path_coords': [[local_graph.nodes[node]['y'], local_graph.nodes[node]['x']] for node in best_path]
            }

        return jsonify({'results': results, 'animation_data': animation_data, 'fastest_algo': fastest_algo_name})

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({'error': f"Could not find one or both locations in the Mumbai map. Please try again. Error: {e}"}), 400

if __name__ == '__main__':
    load_graph()
    app.run(debug=True)