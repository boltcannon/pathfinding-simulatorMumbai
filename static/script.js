document.addEventListener('DOMContentLoaded', () => {
    const findRouteBtn = document.getElementById('find-route-btn');
    const statusEl = document.getElementById('status');
    const resultsTableBody = document.querySelector('#results-table tbody');
    const fastestAlgoEl = document.getElementById('stats-fastest');
    const algoSelect = document.getElementById('algo-select');
    const algoDescEl = document.getElementById('algo-description');
    let map = null;
    let animationLayers = L.layerGroup();

    // Algorithm descriptions
    const descriptions = {
        'a_star': "A* (A-Star) explores by prioritizing paths that are both short and headed towards the goal, making it very efficient.",
        'dijkstra': "Dijkstra's guarantees the shortest path by exploring outwards from the start, checking every nearest unvisited cell.",
        'greedy_bfs': "Greedy BFS always moves to the cell that appears closest to the goal. It's very fast but can be easily tricked by traps.",
        'bfs': "Breadth-First Search (BFS) explores layer by layer, like ripples in a pond. It's simple and guarantees the shortest path.",
        'dfs': "Depth-First Search (DFS) dives as deep as possible down one path before backtracking. It finds a path quickly, but it won't be the shortest."
    };

    // Initialize map
    function initMap() {
        if (map) return;
        map = L.map('map-container').setView([19.0760, 72.8777], 12); // Mumbai default
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
    }

    // Update description panel
    function updateDescription() {
        if (algoDescEl) {
            const selectedAlgoKey = algoSelect.value
                .toLowerCase()
                .replace(/\s+/g, '_')
                .replace('*', '_star');
            algoDescEl.textContent = descriptions[selectedAlgoKey] || "Select an algorithm to learn more.";
        }
    }

    // Handle "Find Route" button
    findRouteBtn.addEventListener('click', async () => {
        const startLocation = document.getElementById('start-location').value.trim();
        const endLocation = document.getElementById('end-location').value.trim();

        if (!startLocation || !endLocation) {
            statusEl.textContent = '⚠️ Please enter both a start and end location.';
            return;
        }

        findRouteBtn.disabled = true;
        statusEl.textContent = '⏳ Comparing algorithms... This may take a moment.';
        resultsTableBody.innerHTML = '<tr><td colspan="4">Calculating...</td></tr>';
        fastestAlgoEl.textContent = '--';

        try {
            const response = await fetch(`/api/compare_routes?start=${encodeURIComponent(startLocation)}&end=${encodeURIComponent(endLocation)}`);
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Populate results table
            resultsTableBody.innerHTML = '';
            data.results.forEach(result => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${result.algo}</td>
                    <td>${result.distance}</td>
                    <td>${result.time}</td>
                    <td>${result.visited}</td>
                `;
                resultsTableBody.appendChild(row);
            });

            // Fastest algorithm highlight
            fastestAlgoEl.textContent = data.fastest_algo || 'N/A';

            // Run animation if path found
            if (data.animation_data && Array.isArray(data.animation_data.path_coords) && data.animation_data.path_coords.length > 0) {
                statusEl.textContent = '✅ Comparison complete! Animating best path...';
                runAnimation(data.animation_data);
            } else {
                statusEl.textContent = 'ℹ️ Comparison complete, but no valid path was found.';
                animationLayers.clearLayers();
            }

        } catch (error) {
            console.error("Route error:", error);
            statusEl.textContent = `❌ Error: ${error.message}`;
            resultsTableBody.innerHTML = '<tr><td colspan="4">An error occurred.</td></tr>';
        } finally {
            findRouteBtn.disabled = false;
        }
    });

    // Animate visited nodes + final path
    async function runAnimation(animData) {
        animationLayers.clearLayers();

        // Visited nodes
        if (animData.visited_coords) {
            for (const coord of animData.visited_coords) {
                L.circle(coord, {
                    radius: 10,
                    color: '#ff00ff', // magenta
                    fillOpacity: 0.3,
                    weight: 1,
                    interactive: false
                }).addTo(animationLayers);
            }
        }

        // Final path polyline
        if (animData.path_coords) {
            const pathPolyline = L.polyline(animData.path_coords, {
                color: 'cyan',
                weight: 5,
                opacity: 1
            }).addTo(animationLayers);

            map.flyToBounds(pathPolyline.getBounds(), { padding: [50, 50] });
        }

        animationLayers.addTo(map);
        statusEl.textContent = '🎬 Animation finished!';
    }

    // Initialize everything
    initMap();
    algoSelect.addEventListener('change', updateDescription);
    updateDescription();
});
