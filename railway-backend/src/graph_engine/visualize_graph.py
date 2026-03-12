"""
visualize_graph.py
------------------
Generates an interactive HTML visualization of the railway network
using PyVis — exactly as required by Phase 2 Member 1 task spec.

Usage:
    python src/graph_engine/visualize_graph.py

Output:
    data/processed/railway_network.html    (interactive PyVis graph)
    data/processed/railway_network.png     (static PNG for reports)
"""

import os
import sys
import pandas as pd
import networkx as nx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
sys.path.insert(0, BASE_DIR)

from src.graph_engine.graph_utils import load_graph, get_station_importance


# ══════════════════════════════════════════════════════════════════════════
#  PYVIS VISUALIZATION  (Phase 2 Member 1 — task spec requirement)
# ══════════════════════════════════════════════════════════════════════════

def generate_pyvis_visualization(G: nx.DiGraph, output_path: str):
    """
    Generate interactive HTML using PyVis — as per task spec:

        from pyvis.network import Network
        net = Network()
        net.add_node("Mumbai")
        net.add_node("Surat")
        net.add_edge("Mumbai","Surat")
        net.show("graph.html")

    Extended with:
      - Node sizing by betweenness centrality
      - Node colouring by delay risk (red=high, orange=medium, blue=low)
      - Edge tooltips showing distance + avg delay
      - Physics-based layout
    """
    from pyvis.network import Network

    # Load centrality + delay risk for styling
    imp_path = os.path.join(PROC_DIR, "station_importance.csv")
    centrality    = {}
    delay_risk    = {}
    avg_delay_map = {}

    if os.path.exists(imp_path):
        df_imp = pd.read_csv(imp_path)
        for _, row in df_imp.iterrows():
            name = row["station_name"]
            centrality[name]    = float(row.get("betweenness_centrality", 0))
            delay_risk[name]    = float(row.get("delay_risk_score", 0))
            avg_delay_map[name] = float(row.get("avg_delay_min", 0) or 0)

    # ── Create PyVis network (task spec) ──────────────────────────────────
    net = Network(
        height="750px",
        width="100%",
        bgcolor="#0d1117",
        font_color="#e6edf3",
        directed=True,
        notebook=False,
    )

    net.set_options("""
    {
      "physics": {
        "enabled": true,
        "barnesHut": {
          "gravitationalConstant": -8000,
          "centralGravity": 0.3,
          "springLength": 120,
          "springConstant": 0.04,
          "damping": 0.09
        },
        "stabilization": { "iterations": 150 }
      },
      "edges": {
        "arrows": { "to": { "enabled": true, "scaleFactor": 0.5 } },
        "color": { "color": "#334155", "highlight": "#f97316" },
        "smooth": { "type": "continuous" }
      },
      "interaction": {
        "hover": true,
        "tooltipDelay": 100,
        "navigationButtons": true
      }
    }
    """)

    # ── Add nodes ─────────────────────────────────────────────────────────
    for node in G.nodes():
        bc   = centrality.get(node, 0)
        risk = delay_risk.get(node, 0)
        dly  = avg_delay_map.get(node, 0)

        size = max(10, min(40, 10 + bc * 500))

        if risk > 40:   color = "#e74c3c"
        elif risk > 20: color = "#f39c12"
        else:           color = "#3498db"

        tooltip = (
            f"Station: {node}\n"
            f"Betweenness: {bc:.4f}\n"
            f"Delay Risk: {risk:.1f}/100\n"
            f"Avg Delay: {dly:.1f} min"
        )

        net.add_node(node, label=node, size=size, color=color, title=tooltip,
                     font={"size": 10, "color": "#e6edf3"})

    # ── Add edges ─────────────────────────────────────────────────────────
    for src, dst, data in G.edges(data=True):
        dist  = data.get("distance", 0)
        tt    = data.get("travel_time", 0)
        delay = data.get("avg_delay", 0)

        tooltip = (
            f"{src} → {dst}\n"
            f"Distance: {dist:.0f} km\n"
            f"Travel time: {tt:.0f} min\n"
            f"Avg delay: {delay:.1f} min"
        )

        net.add_edge(src, dst, title=tooltip, width=1)

    # ── Save HTML ─────────────────────────────────────────────────────────
    net.show(output_path, notebook=False)
    print(f"  ✅ PyVis interactive HTML → {output_path}")


# ══════════════════════════════════════════════════════════════════════════
#  STATIC PNG  (matplotlib — for reports)
# ══════════════════════════════════════════════════════════════════════════

def generate_static_png(G: nx.DiGraph, output_path: str):
    """Generate a static PNG using matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
    except ImportError:
        print("  ⚠️  matplotlib not available — skipping PNG export")
        return

    imp_path   = os.path.join(PROC_DIR, "station_importance.csv")
    centrality = {}
    if os.path.exists(imp_path):
        df_imp = pd.read_csv(imp_path)
        for _, row in df_imp.iterrows():
            centrality[row["station_name"]] = float(row["betweenness_centrality"])

    pos = {}
    for node, data in G.nodes(data=True):
        lat = data.get("latitude")
        lon = data.get("longitude")
        if lat and lon:
            pos[node] = (lon, lat)

    if len(pos) < len(G.nodes) * 0.5:
        pos = nx.spring_layout(G, seed=42, k=2)

    fig, ax = plt.subplots(1, 1, figsize=(20, 14))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    node_colors, node_sizes = [], []
    for node in G.nodes():
        bc = centrality.get(node, 0)
        node_sizes.append(max(50, min(800, 50 + bc * 8000)))
        if bc > 0.1:    node_colors.append("#e74c3c")
        elif bc > 0.05: node_colors.append("#f39c12")
        elif bc > 0.01: node_colors.append("#3498db")
        else:           node_colors.append("#95a5a6")

    nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.15, edge_color="#ffffff",
                           arrows=False, width=0.5)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                           node_size=node_sizes, alpha=0.9)

    try:
        top_stations = set(get_station_importance(20)["station_name"].tolist())
        label_pos    = {n: p for n, p in pos.items() if n in top_stations and n in G.nodes()}
        nx.draw_networkx_labels(G, label_pos, labels={n: n for n in label_pos},
                                ax=ax, font_size=7, font_color="#ffffff", font_weight="bold")
    except Exception:
        pass

    ax.set_title("Indian Railway Network — Station Importance Map",
                 color="#58a6ff", fontsize=16, pad=20, fontweight="bold")
    ax.axis("off")

    legend_patches = [
        mpatches.Patch(color="#e74c3c", label="Critical hub (BC > 0.10)"),
        mpatches.Patch(color="#f39c12", label="Important (BC > 0.05)"),
        mpatches.Patch(color="#3498db", label="Standard station"),
        mpatches.Patch(color="#95a5a6", label="Minor station"),
    ]
    ax.legend(handles=legend_patches, loc="lower left", framealpha=0.3,
              facecolor="#161b22", edgecolor="#30363d", labelcolor="white", fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight",
                facecolor="#0d1117", edgecolor="none")
    plt.close()
    print(f"  ✅ Static PNG → {output_path}")


# ══════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  Indian Railways — Graph Visualisation (PyVis)")
    print("=" * 60)

    G = load_graph()
    print(f"\n  Graph: {G.number_of_nodes()} stations, {G.number_of_edges()} routes")

    html_path = os.path.join(PROC_DIR, "railway_network.html")
    png_path  = os.path.join(PROC_DIR, "railway_network.png")

    print("\n[1/2] Generating PyVis interactive HTML …")
    generate_pyvis_visualization(G, html_path)

    print("\n[2/2] Generating static PNG …")
    generate_static_png(G, png_path)

    print("\n" + "=" * 60)
    print("  Open in browser:  data/processed/railway_network.html")
    print("=" * 60)


if __name__ == "__main__":
    main()
