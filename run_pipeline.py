"""
run_pipeline.py
---------------
One command to run the complete Data + Graph Layer pipeline
using REAL datasets:
  - etrain_delays.csv   (1,900 real train-station delay records)
  - IRI-longestroutes.pdf (70 long-distance routes with distances)

Usage:
    python run_pipeline.py
"""

import os, sys, time
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

def section(title):
    print("\n" + "━"*60)
    print(f"  {title}")
    print("━"*60)

def main():
    start = time.time()
    print("\n"+"═"*60)
    print("  🚂  AI-Powered Railway Intelligence System")
    print("      Data & Graph Layer Pipeline  [v2 — Real Data]")
    print("═"*60)

    section("STEP 1 — Parse PDF Routes (IRI Longest Routes)")
    from src.parse_pdf_routes import main as pdf_main
    pdf_main()

    section("STEP 2 — Preprocess Real Data (etrain + PDF)")
    from src.data_preprocessing import main as pre_main
    pre_main()

    section("STEP 3 & 4 — Build Graph + Centrality Analytics")
    from src.graph_engine.build_graph import main as graph_main
    G = graph_main()

    section("STEP 5 — Train WL Confirmation Model (LogisticRegression)")
    from src.ml_models.wl_model import train_wl_model
    train_wl_model(save=True)

    section("STEP 6 — Generate Visualisation (PyVis)")
    from src.graph_engine.visualize_graph import main as viz_main
    viz_main()

    section("STEP 7 — Verify Integration Files")
    proc_dir = os.path.join(BASE_DIR, "data", "processed")
    expected = [
        ("graph_edges.csv",           "Edges for ML + dashboard"),
        ("stations_clean.csv",        "Stations for dashboard map"),
        ("station_importance.csv",    "Centrality + delay risk"),
        ("station_delay_stats.csv",   "Per-station delay stats for ML"),
        ("schedule_features.csv",     "ML feature table (etrain)"),
        ("routes.csv",                "Full route table"),
        ("stations.csv",              "Full station table with codes"),
        ("railway_network.html",      "Interactive graph for dashboard"),
        ("railway_network.png",       "Static map for reports"),
    ]
    all_ok = True
    for fname, desc in expected:
        fpath = os.path.join(proc_dir, fname)
        ok    = os.path.exists(fpath)
        size  = f"{os.path.getsize(fpath):,} bytes" if ok else "MISSING"
        icon  = "✅" if ok else "❌"
        print(f"  {icon}  {fname:35s}  {size:15s}  ← {desc}")
        if not ok: all_ok = False

    elapsed = time.time() - start
    print("\n"+"═"*60)
    status = "✅ Pipeline complete" if all_ok else "⚠️  Pipeline finished with warnings"
    print(f"  {status} in {elapsed:.1f}s")
    print("""
  ┌──────────────────────────────────────────────────────┐
  │  FOR TEAMMATES                                       │
  │                                                      │
  │  ML Delay Prediction:                                │
  │    data/processed/schedule_features.csv  (etrain)   │
  │    data/processed/station_delay_stats.csv            │
  │    data/processed/station_importance.csv             │
  │                                                      │
  │  ML Ticket Prediction:                               │
  │    data/raw/railway_reservation_dataset.csv          │
  │                                                      │
  │  Dashboard:                                          │
  │    data/processed/stations_clean.csv  (lat/lon map)  │
  │    data/processed/graph_edges.csv     (network)      │
  │    data/processed/railway_network.html (interactive) │
  │                                                      │
  │  Graph API:                                          │
  │    from src.graph_engine.graph_utils import          │
  │        load_graph, shortest_route, get_delay_stats   │
  └──────────────────────────────────────────────────────┘
""")

if __name__ == "__main__":
    main()
