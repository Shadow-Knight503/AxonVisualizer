import json
import sys
import colorsys
import requests

from PyQt6.QtCore import QUrl, Qt, pyqtSlot, QObject
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QDialog
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage


def fetch_data_from_endpoint(url):
    """Fetches network or node JSON data from the given API endpoint."""
    try:
        print(f"[Python] Requesting data from: {url}")
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            print(f"[Python] Successfully fetched data from {url}")
            return response.json()
    except Exception as e:
        print(f"[Python] Connection error to {url}: {e}")
    return None


def hex_to_hsv(hex_str):
    hex_str = hex_str.lstrip('#')
    r = int(hex_str[0:2], 16) / 255.0
    g = int(hex_str[2:4], 16) / 255.0
    b = int(hex_str[4:6], 16) / 255.0
    return colorsys.rgb_to_hsv(r, g, b)


def hsv_to_hex(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return '#{:02x}{:02x}{:02x}'.format(int(r * 255), int(g * 255), int(b * 255))


def generate_custom_color_palette(n, start_hex="#3b82f6", end_hex="#ec4899"):
    colors = []
    if n <= 0:
        return colors
    h1, s1, v1 = hex_to_hsv(start_hex)
    h2, s2, v2 = hex_to_hsv(end_hex)
    for i in range(n):
        t = i / max(n - 1, 1)
        h = h1 + (h2 - h1) * t
        s = s1 + (s2 - s1) * t
        v = v1 + (v2 - v1) * t
        colors.append(hsv_to_hex(h, s, v))
    return colors


def build_network_html(data, view_mode="relation"):
    """Generates the Vis.js network HTML template cleanly without syntax errors."""
    nodes_data = []
    edges_data = []

    if data:
        try:
            if view_mode == "relation":
                nodes_set = set()
                for edge in data:
                    from_node = edge["from"]
                    to_node = edge["to"]
                    label = edge.get("label", "")

                    nodes_set.add(from_node)
                    nodes_set.add(to_node)

                    calculated_length = max(180, len(label) * 16 + 120)

                    edges_data.append({
                        "from": from_node,
                        "to": to_node,
                        "label": label,
                        "length": calculated_length,
                        "arrows": {"to": {"enabled": True, "scaleFactor": 1.5}},
                        "color": {"color": "#475569", "highlight": "#38bdf8"},
                        "font": {
                            "color": "#f8fafc", "size": 12, "face": "Georgia, serif",
                            "align": "middle", "background": "#0f172a", "strokeWidth": 0
                        }
                    })

                unique_nodes = sorted(list(nodes_set))
                node_colors = generate_custom_color_palette(len(unique_nodes), "#3b82f6", "#ec4899")

                for idx, node in enumerate(unique_nodes):
                    nodes_data.append({
                        "id": node, "label": node, "title": f"Node Details: {node}",
                        "shape": "box", "margin": 18, "borderRadius": 10,
                        "color": {"background": "#111827", "border": node_colors[idx],
                                  "highlight": {"background": "#1f2937", "border": "#ffffff"}},
                        "font": {"color": "#f3f4f6", "size": 13, "face": "Georgia, serif"}
                    })

            elif view_mode == "nodes":
                parent_nodes_set = set()
                for item in data:
                    parent = item.get("parentnode")
                    if parent:
                        parent_nodes_set.add(parent)

                parent_colors = generate_custom_color_palette(len(parent_nodes_set), "#f97316", "#eab308")
                for idx, parent in enumerate(sorted(list(parent_nodes_set))):
                    nodes_data.append({
                        "id": parent, "label": parent, "title": f"Parent Category: {parent}",
                        "shape": "box", "margin": 20, "borderRadius": 12,
                        "color": {"background": "#1c1917", "border": parent_colors[idx],
                                  "highlight": {"background": "#292524", "border": "#ffffff"}},
                        "font": {"color": "#fed7aa", "size": 15, "face": "Georgia, serif", "bold": True}
                    })

                child_colors = generate_custom_color_palette(len(data), "#06b6d4", "#3b82f6")
                for idx, item in enumerate(data):
                    node_id = item.get("id")
                    label = item.get("label")
                    parent = item.get("parentnode")

                    nodes_data.append({
                        "id": node_id, "label": f"{node_id}\n({label})", "title": f"Item: {label}",
                        "shape": "box", "margin": 14, "borderRadius": 8,
                        "color": {"background": "#111827", "border": child_colors[idx],
                                  "highlight": {"background": "#1f2937", "border": "#ffffff"}},
                        "font": {"color": "#e0f2fe", "size": 12, "face": "Georgia, serif"}
                    })

                    if parent:
                        edges_data.append({
                            "from": parent, "to": node_id, "label": "belongs to",
                            "length": 150, "arrows": {"to": {"enabled": True, "scaleFactor": 1.2}},
                            "color": {"color": "#475569", "highlight": "#38bdf8"},
                            "font": {"color": "#94a3b8", "size": 10, "face": "Georgia, serif", "align": "middle",
                                     "background": "#0f172a", "strokeWidth": 0}
                        })
        except Exception as e:
            print(f"[Python] Error parsing data for {view_mode}: {e}")

    if not nodes_data:
        nodes_data = [{"id": "Status", "label": "No data returned from endpoint...", "shape": "box",
                       "color": {"background": "#1f2937", "border": "#ef4444"},
                       "font": {"color": "#f87171", "face": "Georgia, serif"}}]

    mode_btn_text = "Mode: Node Map" if view_mode == "relation" else "Mode: Relation Map"
    mode_btn_class = "tool-btn" if view_mode == "relation" else "tool-btn active-mode"

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Network Visualizer</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        html, body {{
            width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden;
            background-color: #030712; font-family: Georgia, serif; letter-spacing: 0.6px;
        }}
        #mynetwork {{ width: 100%; height: 100%; background-color: #030712; }}

        #toolbar {{
            position: absolute; top: 15px; left: 15px; z-index: 10;
            background: rgba(17, 24, 39, 0.95); padding: 10px 14px; border-radius: 8px;
            border: 1px solid #374151; display: flex; gap: 12px; align-items: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
        }}
        .tool-btn {{
            background-color: #0284c7; color: white; border: none; padding: 6px 12px;
            border-radius: 4px; cursor: pointer; font-family: Georgia, serif; font-size: 12px; font-weight: bold;
            transition: background 0.2s;
        }}
        .tool-btn:hover {{ background-color: #0369a1; }}
        .tool-btn.frozen {{ background-color: #dc2626; }}
        .tool-btn.active-mode {{ background-color: #10b981; }}

        .color-picker-group {{ display: flex; align-items: center; gap: 5px; color: #9ca3af; font-size: 11px; }}
        input[type="color"] {{ border: none; width: 24px; height: 24px; border-radius: 4px; cursor: pointer; background: none; }}

        #drawer {{
            position: absolute; top: 70px; left: 15px; bottom: 70px; width: 240px;
            background: rgba(17, 24, 39, 0.95); border: 1px solid #374151; border-radius: 8px; z-index: 9;
            display: flex; flex-direction: column; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            transition: transform 0.3s ease;
        }}
        #drawer.closed {{ transform: translateX(-270px); }}
        #drawer-header {{
            padding: 10px 12px; font-weight: bold; font-size: 13px; color: #38bdf8;
            border-bottom: 1px solid #374151; display: flex; justify-content: space-between; align-items: center;
        }}
        #node-list {{ overflow-y: auto; flex: 1; padding: 6px; }}
        .node-item {{
            padding: 6px 10px; font-size: 12px; color: #f3f4f6; cursor: pointer; border-radius: 4px;
            margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }}
        .node-item:hover {{ background-color: #1f2937; color: #38bdf8; }}

        #refresh-btn {{
            position: absolute; bottom: 20px; right: 20px; z-index: 10;
            background: #1e293b; color: #38bdf8; border: 1px solid #334151; width: 45px; height: 45px;
            border-radius: 50%; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5); transition: background 0.2s, transform 0.2s;
        }}
        #refresh-btn:hover {{ background: #0f172a; transform: scale(1.05); }}

        #instructions {{
            position: absolute; bottom: 20px; left: 20px; color: #9ca3af; font-size: 11px;
            pointer-events: none; background: rgba(17, 24, 39, 0.9); padding: 8px 12px;
            border-radius: 6px; border: 1px solid #374151; z-index: 8;
        }}
    </style>
</head>
<body>
    <div id="toolbar">
        <button class="tool-btn" onclick="toggleDrawer()">📁 Locator</button>
        <button id="physics-toggle" class="tool-btn" onclick="togglePhysics()">Freeze: OFF</button>
        <!-- Clean safe internal navigation URL command -->
        <button id="mode-toggle" class="{mode_btn_class}" onclick="window.location.href = 'pycommand://toggle_mode';">{mode_btn_text}</button>
        <div class="color-picker-group">
            <label>Start:</label>
            <input type="color" id="color-start" value="#3b82f6" onchange="updateColors()">
        </div>
        <div class="color-picker-group">
            <label>End:</label>
            <input type="color" id="color-end" value="#ec4899" onchange="updateColors()">
        </div>
    </div>

    <div id="drawer" class="closed">
        <div id="drawer-header">
            <span>Nodes List</span>
            <span style="cursor:pointer; font-size:14px;" onclick="toggleDrawer()">✕</span>
        </div>
        <div id="node-list"></div>
    </div>

    <button id="refresh-btn" title="Reload Data" onclick="window.location.href = 'pycommand://reload_data';">🔄</button>

    <div id="mynetwork"></div>
    <div id="instructions">💡 Tip: Click node to highlight chain. Use toggle to switch views.</div>

    <script type="text/javascript">
        var nodesData = {json.dumps(nodes_data)};
        var edgesData = {json.dumps(edges_data)};

        var nodes = new vis.DataSet(nodesData);
        var edges = new vis.DataSet(edgesData);

        var container = document.getElementById('mynetwork');
        var data = {{ nodes: nodes, edges: edges }};

        var options = {{
            nodes: {{ borderWidth: 2, shadow: false }},
            edges: {{ width: 2, smooth: {{ type: 'cubicBezier', roundness: 0.2 }}, shadow: false }},
            physics: {{
                barnesHut: {{ gravitationalConstant: -8000, centralGravity: 0.2, springConstant: 0.02, avoidOverlap: 0.5 }},
                stabilization: {{ enabled: true, iterations: 1000 }}
            }},
            interaction: {{ hover: true, tooltipDelay: 200, hideEdgesOnDrag: false, hideNodesOnDrag: false }}
        }};

        var network = new vis.Network(container, data, options);

        function populateNodeList() {{
            let listContainer = document.getElementById('node-list');
            listContainer.innerHTML = '';
            let allNodesArr = nodes.get({{returnType: "Object"}});
            let sortedIds = Object.keys(allNodesArr).sort();

            sortedIds.forEach(id => {{
                let item = document.createElement('div');
                item.className = 'node-item';
                item.innerText = id;
                item.onclick = function() {{ focusOnNode(id); }};
                listContainer.appendChild(item);
            }});
        }}
        populateNodeList();

        function toggleDrawer() {{
            document.getElementById('drawer').classList.toggle('closed');
        }}

        function focusOnNode(nodeId) {{
            network.selectNodes([nodeId]);
            network.focus(nodeId, {{ scale: 1.2, animation: {{ duration: 800, easingFunction: 'easeInOutQuad' }} }});
            triggerHighlightForNode(nodeId);
        }}

        var physicsEnabled = true;
        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: physicsEnabled }});
            let btn = document.getElementById('physics-toggle');
            if (physicsEnabled) {{
                btn.innerText = "Freeze: OFF";
                btn.classList.remove('frozen');
            }} else {{
                btn.innerText = "Freeze: ON";
                btn.classList.add('frozen');
            }}
        }}

        function hexToRgb(hex) {{
            let bigint = parseInt(hex.replace('#',''), 16);
            return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
        }}
        function rgbToHex(r, g, b) {{
            return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
        }}
        function updateColors() {{
            let startHex = document.getElementById('color-start').value;
            let endHex = document.getElementById('color-end').value;
            let c1 = hexToRgb(startHex);
            let c2 = hexToRgb(endHex);

            let allNodesArr = nodes.get({{returnType: "Object"}});
            let ids = Object.keys(allNodesArr).sort();
            let n = ids.length;

            let updates = [];
            ids.forEach((id, idx) => {{
                let t = n > 1 ? idx / (n - 1) : 0;
                let r = Math.round(c1[0] + (c2[0] - c1[0]) * t);
                let g = Math.round(c1[1] + (c2[1] - c1[1]) * t);
                let b = Math.round(c1[2] + (c2[2] - c1[2]) * t);
                let newColor = rgbToHex(r, g, b);

                let node = allNodesArr[id];
                node.color.border = newColor;
                updates.push(node);
            }});
            nodes.update(updates);
        }}

        let allNodes = nodes.get({{returnType: "Object"}});
        let allEdges = edges.get({{returnType: "Object"}});
        let activeSelectedNodeId = null;

        function resetHighlight() {{
            let resetNodes = [];
            for (let nodeId in allNodes) {{
                let node = allNodes[nodeId];
                node.opacity = 1.0;
                resetNodes.push(node);
            }}
            let resetEdges = [];
            for (let edgeId in allEdges) {{
                let edge = allEdges[edgeId];
                edge.color = {{ color: "#475569", opacity: 1.0 }};
                edge.width = 2;
                resetEdges.push(edge);
            }}
            nodes.update(resetNodes);
            edges.update(resetEdges);
            activeSelectedNodeId = null;
        }}

        function triggerHighlightForNode(clickedNodeId) {{
            if (activeSelectedNodeId === clickedNodeId) {{
                resetHighlight();
                return;
            }}
            activeSelectedNodeId = clickedNodeId;

            let connectedNodes = network.getConnectedNodes(clickedNodeId);
            connectedNodes.push(clickedNodeId);
            let connectedEdges = network.getConnectedEdges(clickedNodeId);

            let updateArrayNodes = [];
            for (let nodeId in allNodes) {{
                let node = allNodes[nodeId];
                if (connectedNodes.includes(nodeId)) {{
                    node.opacity = 1.0;
                }} else {{
                    node.opacity = 0.20;
                }}
                updateArrayNodes.push(node);
            }}

            let updateArrayEdges = [];
            for (let edgeId in allEdges) {{
                let edge = allEdges[edgeId];
                if (connectedEdges.includes(edgeId)) {{
                    edge.color = {{ color: "#38bdf8", opacity: 1.0 }};
                    edge.width = 3;
                }} else {{
                    edge.color = {{ color: "#1f2937", opacity: 0.15 }};
                    edge.width = 1;
                }}
                updateArrayEdges.push(edge);
            }}

            nodes.update(updateArrayNodes);
            edges.update(updateArrayEdges);
        }}

        network.on("click", function (params) {{
            if (params.nodes.length > 0) {{
                triggerHighlightForNode(params.nodes[0]);
            }} else {{
                resetHighlight();
            }}
        }});
    </script>
</body>
</html>
"""
    return html_content


class LoggedPage(QWebEnginePage):
    """Intercepts custom pycommand:// navigation instantly without triggering external OS apps."""

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        print(f"[JS Console] Line {lineNumber}: {message}")

    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        url_str = url.toString()
        if url_str.startswith("pycommand://"):
            command = url_str.replace("pycommand://", "")
            if command == "toggle_mode":
                print("[Python] Intercepted command: toggle_mode")
                self.main_window.toggle_view_mode()
            elif command == "reload_data":
                print("[Python] Intercepted command: reload_data")
                self.main_window.reload_graph_view()
            return False  # Block actual browser navigation
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)


class EndpointDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.url = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Network Visualizer - Configuration")
        self.resize(460, 150)
        self.setStyleSheet("background-color: #030712; color: #f9fafb; font-family: Georgia, serif;")

        layout = QVBoxLayout()
        label = QLabel("Enter host and port (e.g., localhost:8000):")
        label.setStyleSheet("font-size: 13px; color: #38bdf8; font-weight: bold;")
        layout.addWidget(label)

        self.input_box = QLineEdit()
        self.input_box.setText("localhost:8000")
        self.input_box.setStyleSheet(
            "padding: 8px; font-size: 12px; background-color: #111827; border: 1px solid #374151; border-radius: 4px; color: white;")
        layout.addWidget(self.input_box)

        btn = QPushButton("Launch Visualizer")
        btn.setStyleSheet(
            "background-color: #0284c7; color: white; font-weight: bold; padding: 10px; border-radius: 4px; margin-top: 8px;")
        btn.clicked.connect(self.on_submit)
        layout.addWidget(btn)
        self.setLayout(layout)

    def on_submit(self):
        raw_input = self.input_box.text().strip()
        if raw_input:
            clean_host = raw_input.replace("http://", "").replace("https://", "").strip("/")
            self.base_url = f"http://{clean_host}"
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Please enter a valid host and port.")


class MainWindow(QMainWindow):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.current_mode = "relation"  # "relation" or "nodes"

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Dynamic Network Visualizer - Connected to {self.base_url}")
        self.resize(1200, 800)

        self.browser = QWebEngineView()

        # Attach LoggedPage which handles custom pycommand:// clicks internally
        self.page = LoggedPage(self)
        self.browser.setPage(self.page)

        self.setCentralWidget(self.browser)
        self.reload_graph_view()

    def get_current_endpoint(self):
        if self.current_mode == "relation":
            return f"{self.base_url}/axonapi/relation"
        else:
            return f"{self.base_url}/axonapi/getnodes"

    def reload_graph_view(self):
        endpoint = self.get_current_endpoint()
        print(f"[Python] Fetching data from: {endpoint} [Mode: {self.current_mode}]")
        data = fetch_data_from_endpoint(endpoint)
        html_content = build_network_html(data, self.current_mode)
        self.browser.setHtml(html_content, QUrl("http://localhost"))

    def toggle_view_mode(self):
        if self.current_mode == "relation":
            self.current_mode = "nodes"
        else:
            self.current_mode = "relation"

        print(f"[Python] Toggled mode to: {self.current_mode}")
        self.reload_graph_view()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    dialog = EndpointDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted and hasattr(dialog, "base_url"):
        main_win = MainWindow(dialog.base_url)
        main_win.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)
