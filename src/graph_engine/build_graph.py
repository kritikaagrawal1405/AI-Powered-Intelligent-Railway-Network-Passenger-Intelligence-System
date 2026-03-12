"""
build_graph.py
--------------
Builds a directed NetworkX graph from REAL etrain + PDF data.

Nodes  = stations (with lat/lon)
Edges  = routes   (distance, travel_time, avg_delay_on_edge)

Usage:
    python src/graph_engine/build_graph.py
"""

import os, sys
import pandas as pd
import networkx as nx

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(PROC_DIR, exist_ok=True)
sys.path.insert(0, BASE_DIR)


def build_railway_graph() -> nx.DiGraph:
    edges_path    = os.path.join(PROC_DIR, "graph_edges.csv")
    stations_path = os.path.join(PROC_DIR, "stations_clean.csv")

    if not os.path.exists(edges_path):
        raise FileNotFoundError(
            f"Missing {edges_path}\n"
            "Run the pipeline first:\n"
            "  python src/parse_pdf_routes.py\n"
            "  python src/data_preprocessing.py"
        )

    df_edges    = pd.read_csv(edges_path)
    df_stations = pd.read_csv(stations_path) if os.path.exists(stations_path) else pd.DataFrame()

    station_attrs = {}
    if not df_stations.empty:
        for _, r in df_stations.iterrows():
            station_attrs[r["station_name"]] = {
                "latitude":  r.get("latitude"),
                "longitude": r.get("longitude"),
            }

    G = nx.DiGraph()

    for _, row in df_edges.iterrows():
        src = str(row["source_station"])
        dst = str(row["destination_station"])
        for name in (src, dst):
            if name not in G.nodes:
                G.add_node(name, **station_attrs.get(name, {}))

        dist  = float(row["distance"])  if pd.notna(row.get("distance"))    else 0.0
        tt    = float(row["travel_time"]) if pd.notna(row.get("travel_time")) else 0.0
        delay = float(row["avg_delay_on_edge"]) if pd.notna(row.get("avg_delay_on_edge")) else 0.0

        G.add_edge(src, dst,
                   distance          = dist,
                   travel_time       = tt,
                   avg_delay         = delay,
                   weight            = dist if dist > 0 else 1.0,
                   weight_delay      = delay if delay > 0 else 1.0)
    return G


def compute_centrality(G: nx.DiGraph) -> pd.DataFrame:
    print("  Computing betweenness centrality …")
    betweenness = nx.betweenness_centrality(G, weight="weight", normalized=True)
    degree      = nx.degree_centrality(G)
    in_deg      = dict(G.in_degree())
    out_deg     = dict(G.out_degree())

    rows = []
    for node in G.nodes():
        rows.append({
            "station_name":           node,
            "betweenness_centrality": round(betweenness.get(node, 0), 6),
            "degree_centrality":      round(degree.get(node, 0), 6),
            "in_degree":              in_deg.get(node, 0),
            "out_degree":             out_deg.get(node, 0),
            "total_degree":           in_deg.get(node, 0) + out_deg.get(node, 0),
        })

    df = pd.DataFrame(rows).sort_values("betweenness_centrality", ascending=False).reset_index(drop=True)
    df["importance_rank"] = df.index + 1
    return df


def export_graph_data(G: nx.DiGraph):
    edges = []
    for src, dst, data in G.edges(data=True):
        edges.append({
            "source_station":      src,
            "destination_station": dst,
            "distance":            data.get("distance", 0),
            "travel_time":         data.get("travel_time", 0),
            "avg_delay":           data.get("avg_delay", 0),
        })
    df_e = pd.DataFrame(edges)
    df_e.to_csv(os.path.join(PROC_DIR, "graph_edges.csv"), index=False)
    print(f"  ✅ graph_edges.csv  ({len(df_e)} edges)")

    rows = [{"station_name": n,
             "latitude":     d.get("latitude"),
             "longitude":    d.get("longitude")}
            for n, d in G.nodes(data=True)]
    df_s = pd.DataFrame(rows)
    df_s.to_csv(os.path.join(PROC_DIR, "stations_clean.csv"), index=False)
    print(f"  ✅ stations_clean.csv  ({len(df_s)} nodes)")
    return df_e, df_s


def main():
    print("="*60)
    print("  Indian Railways — Graph Construction (Real Data)")
    print("="*60)

    print("\n[1/3] Building directed railway graph …")
    G = build_railway_graph()
    print(f"  ✅ {G.number_of_nodes()} stations, {G.number_of_edges()} routes")

    print("\n[2/3] Computing centrality analytics …")
    df_imp = compute_centrality(G)
    df_imp.to_csv(os.path.join(PROC_DIR, "station_importance.csv"), index=False)
    print(f"  ✅ station_importance.csv")
    print("\n  Top 10 critical stations (betweenness centrality):")
    print(df_imp[["importance_rank","station_name","betweenness_centrality","total_degree"]].head(10).to_string(index=False))

    # Enrich importance with delay risk
    delay_path = os.path.join(PROC_DIR, "station_delay_stats.csv")
    if os.path.exists(delay_path):
        df_delay = pd.read_csv(delay_path)[["station_name","avg_delay_min","delay_risk_score"]]
        df_imp = df_imp.merge(df_delay, on="station_name", how="left")
        df_imp.to_csv(os.path.join(PROC_DIR, "station_importance.csv"), index=False)
        print("  ✅ Enriched station_importance.csv with delay risk scores")

    print("\n[3/3] Exporting integration files …")
    export_graph_data(G)

    print("\n"+"="*60)
    print("  Graph construction complete!")
    print("="*60)
    return G


if __name__ == "__main__":
    main()
