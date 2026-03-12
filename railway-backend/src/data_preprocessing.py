"""
data_preprocessing.py
---------------------
Preprocesses REAL Indian Railways data from:
  1. etrain_delays.csv   — 1,900 train-stop records with actual delay statistics
  2. pdf_routes.csv      — 70 long-distance routes parsed from IRI PDF

Produces clean tables for:
  - Graph construction (stations.csv, routes.csv)
  - ML delay prediction (station_delay_stats.csv, schedule_features.csv)
  - Dashboard (stations_clean.csv)

Usage:
    python src/data_preprocessing.py
"""

import os
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(BASE_DIR, "data", "raw")
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(PROC_DIR, exist_ok=True)

# Full coordinate lookup covering all etrain station codes + PDF stations
STATION_COORDS = {
    "MAS":  ("Chennai Central",       13.0836,  80.2753),
    "AVD":  ("Avadi",                 13.1143,  80.1009),
    "AJJ":  ("Arakkonam",             13.0804,  79.6693),
    "KPD":  ("Katpadi Jn",            12.9295,  79.1324),
    "JTJ":  ("Jolarpettai",           12.5739,  78.5768),
    "SA":   ("Salem Jn",              11.6643,  78.1460),
    "ED":   ("Erode Jn",              11.3410,  77.7172),
    "TUP":  ("Tiruppur",              11.1085,  77.3411),
    "CBF":  ("Coimbatore North",      11.0340,  76.9693),
    "CBE":  ("Coimbatore Jn",         11.0168,  76.9558),
    "MDU":  ("Madurai Jn",             9.9195,  78.1193),
    "TVC":  ("Thiruvananthapuram",     8.4855,  76.9492),
    "TVCN": ("Thiruvananthapuram Nth", 8.5119,  76.9523),
    "NCJ":  ("Nagercoil",              8.1776,  77.4323),
    "TEN":  ("Tirunelveli",            8.7276,  77.7043),
    "CAPE": ("Kanyakumari",            8.0883,  77.5385),
    "TPJ":  ("Tiruchirappalli",       10.8050,  78.6856),
    "MQ":   ("Mannargudi",            10.6627,  79.4521),
    "RMM":  ("Rameswaram",             9.2876,  79.3129),
    "TPTY": ("Tirupati",              13.6288,  79.4192),
    "ERS":  ("Ernakulam Jn",           9.9816,  76.2999),
    "MYS":  ("Mysuru Jn",             12.3051,  76.6551),
    "SBC":  ("Bangalore City",        12.9779,  77.5672),
    "SMVB": ("Bengaluru Cant",        12.9957,  77.5990),
    "YPR":  ("Yesvantpur",            13.0217,  77.5571),
    "VSKP": ("Visakhapatnam",         17.6868,  83.2185),
    "SC":   ("Secunderabad",          17.4339,  78.5006),
    "BZA":  ("Vijayawada",            16.5193,  80.6305),
    "GNT":  ("Guntur",                16.3067,  80.4365),
    "OGL":  ("Ongole",                15.5057,  80.0499),
    "NLR":  ("Nellore",               14.4426,  79.9865),
    "RU":   ("Renigunta",             13.6510,  79.5117),
    "GDR":  ("Gudur",                 14.1489,  79.8553),
    "SLO":  ("Sullurpeta",            13.7626,  79.9981),
    "NZM":  ("Hazrat Nizamuddin",     28.5713,  77.2511),
    "NDLS": ("New Delhi",             28.6419,  77.2194),
    "DLI":  ("Delhi Jn",              28.6581,  77.2300),
    "GZB":  ("Ghaziabad",             28.6692,  77.4538),
    "MTJ":  ("Mathura Jn",            27.4924,  77.6737),
    "AGC":  ("Agra Cantt",            27.1767,  78.0081),
    "JHS":  ("Jhansi Jn",             25.4484,  78.5685),
    "BPL":  ("Bhopal Jn",             23.2599,  77.4126),
    "ET":   ("Itarsi",                22.6133,  77.7594),
    "NGP":  ("Nagpur",                21.1458,  79.0882),
    "BPQ":  ("Balharshah",            19.8616,  79.3688),
    "WADI": ("Wadi",                  17.0741,  76.9760),
    "GR":   ("Gulbarga",              17.3297,  76.8243),
    "DWR":  ("Dharwad",               15.4647,  75.0029),
    "UBL":  ("Hubli",                 15.3647,  75.1240),
    "ASK":  ("Arsikere",              13.3147,  76.2496),
    "HWH":  ("Howrah",                22.5839,  88.3425),
    "BWN":  ("Barddhaman",            23.2324,  87.8615),
    "RNC":  ("Ranchi",                23.3441,  85.3096),
    "DHN":  ("Dhanbad",               23.7957,  86.4304),
    "PNBE": ("Patna Jn",              25.6119,  85.1439),
    "MFP":  ("Muzaffarpur",           26.1209,  85.3647),
    "DBG":  ("Darbhanga",             26.1542,  85.8978),
    "GKP":  ("Gorakhpur",             26.7606,  83.3732),
    "LKO":  ("Lucknow",               26.8467,  80.9462),
    "CNB":  ("Kanpur Central",        26.4499,  80.3319),
    "AYC":  ("Ayodhya Cantt",         26.7956,  82.2040),
    "GD":   ("Gonda",                 27.1350,  81.9650),
    "BJU":  ("Barauni",               25.4717,  86.0012),
    "SHC":  ("Saharsa",               25.8800,  86.5951),
    "ASR":  ("Amritsar",              31.6340,  74.8723),
    "JAT":  ("Jammu Tawi",            32.7266,  74.8570),
    "SVDK": ("Vaishno Devi Katra",    32.9915,  74.9455),
    "CDG":  ("Chandigarh",            30.7333,  76.7794),
    "UMB":  ("Ambala Cantt",          30.3782,  76.8268),
    "SGNR": ("Sri Ganganagar",        29.9175,  73.8629),
    "BKN":  ("Bikaner",               28.0229,  73.3119),
    "JU":   ("Jodhpur",               26.2389,  73.0243),
    "AII":  ("Ajmer",                 26.4499,  74.6399),
    "JP":   ("Jaipur",                26.9124,  75.7873),
    "YNRK": ("Rishikesh",             30.1158,  78.2993),
    "FZR":  ("Firozpur Cantt",        30.9254,  74.6137),
    "GHY":  ("Guwahati",              26.1445,  91.7362),
    "KYQ":  ("Kamakhya",              26.1630,  91.6778),
    "SCL":  ("Silchar",               24.8333,  92.7789),
    "AGTL": ("Agartala",              23.8315,  91.2868),
    "NTSK": ("New Tinsukia",          27.4969,  95.3601),
    "DBRG": ("Dibrugarh",             27.4728,  94.9120),
    "TBM":  ("Tambaram",              12.9249,  80.1000),
    "NJP":  ("New Jalpaiguri",        26.7053,  88.2576),
    "JBN":  ("Jogbani",               26.4014,  87.2644),
    "MMCT": ("Mumbai Central",        18.9693,  72.8194),
    "LTT":  ("Mumbai LTT",            19.0748,  72.9028),
    "CSTM": ("Mumbai CSMT",           18.9398,  72.8354),
    "PUNE": ("Pune Jn",               18.5204,  73.8567),
    "ADI":  ("Ahmedabad",             23.0225,  72.5714),
    "BRC":  ("Vadodara",              22.3072,  73.1812),
    "ST":   ("Surat",                 21.1702,  72.8311),
    "OKHA": ("Okha",                  22.4668,  69.0731),
    "GIMB": ("Gandhidham",            23.0753,  70.1337),
    "RJT":  ("Rajkot",                22.3039,  70.8022),
    "R":    ("Raipur",                21.2514,  81.6296),
    "BSP":  ("Bilaspur",              22.0797,  82.1409),
    "LGH":  ("Lalganj",               25.8704,  82.4008),
    "CHZ":  ("Charlapalli",           17.4069,  78.5657),
    "PER":  ("Perambur",              13.1167,  80.2333),
    "SHM":  ("Shalimar",              22.5524,  88.3192),
}


def load_etrain_delays():
    path = os.path.join(RAW_DIR, "etrain_delays.csv")
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower()
    df["station_name"] = df["station_name"].str.strip().str.title()
    for col in ["average_delay_minutes","pct_right_time","pct_slight_delay","pct_significant_delay","pct_cancelled_unknown"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["station_code","station_name"])
    print(f"  etrain_delays: {len(df)} rows | {df['train_number'].nunique()} trains | {df['station_code'].nunique()} stations")
    return df


def load_pdf_routes():
    path = os.path.join(RAW_DIR, "pdf_routes.csv")
    df = pd.read_csv(path)
    print(f"  pdf_routes:    {len(df)} long-distance routes")
    return df


def build_stations(df_etrain, df_pdf):
    etrain_st = df_etrain[["station_code","station_name"]].drop_duplicates(subset=["station_code"])
    pdf_src   = df_pdf[["source_code","source_station"]].rename(columns={"source_code":"station_code","source_station":"station_name"})
    pdf_dst   = df_pdf[["destination_code","destination_station"]].rename(columns={"destination_code":"station_code","destination_station":"station_name"})
    all_st    = pd.concat([etrain_st, pdf_src, pdf_dst]).drop_duplicates(subset=["station_code"])

    def coords(code):
        if code in STATION_COORDS:
            return STATION_COORDS[code][1], STATION_COORDS[code][2]
        return None, None

    all_st["latitude"]  = all_st["station_code"].apply(lambda c: coords(c)[0])
    all_st["longitude"] = all_st["station_code"].apply(lambda c: coords(c)[1])
    result = all_st.dropna(subset=["latitude","longitude"]).reset_index(drop=True)
    missing = all_st[all_st["latitude"].isna()]
    if len(missing):
        print(f"  ⚠️  {len(missing)} stations skipped (no coordinates): {list(missing['station_code'])[:8]}")
    return result


def build_routes(df_etrain, df_pdf):
    pdf_lookup = {}
    for _, r in df_pdf.iterrows():
        pdf_lookup[str(r["train_no"])] = {"dist": r["distance_km"], "dur": r["duration_min"]}

    edges = []
    for train_no, grp in df_etrain.groupby("train_number"):
        stops = grp.reset_index(drop=True)
        n = len(stops)
        if n < 2: continue
        info = pdf_lookup.get(str(train_no), {})
        total_d = info.get("dist", None)
        total_t = info.get("dur",  None)
        leg_d = round(total_d/(n-1), 1) if total_d else None
        leg_t = round(total_t/(n-1), 1) if total_t else None

        for i in range(n - 1):
            sr, dr = stops.iloc[i], stops.iloc[i+1]
            delay_vals = [v for v in [sr.get("average_delay_minutes"), dr.get("average_delay_minutes")] if pd.notna(v)]
            avg_delay = round(np.mean(delay_vals), 2) if delay_vals else None
            edges.append({
                "source_code":         sr["station_code"],
                "source_station":      sr["station_name"],
                "destination_code":    dr["station_code"],
                "destination_station": dr["station_name"],
                "train_number":        train_no,
                "train_name":          sr.get("train_name",""),
                "distance_km":         leg_d,
                "travel_time_min":     leg_t,
                "avg_delay_on_edge":   avg_delay,
                "pct_right_time_src":  sr.get("pct_right_time", None),
                "pct_significant_delay_src": sr.get("pct_significant_delay", None),
            })

    df_edges = pd.DataFrame(edges)

    # Add PDF direct arcs (src -> dst with real distances)
    pdf_arcs = df_pdf.copy()
    pdf_arcs = pdf_arcs.rename(columns={"duration_min":"travel_time_min","train_no":"train_number"})
    pdf_arcs["avg_delay_on_edge"] = None
    pdf_arcs["pct_right_time_src"] = None
    pdf_arcs["pct_significant_delay_src"] = None
    pdf_arcs = pdf_arcs[list(df_edges.columns)]

    combined = pd.concat([df_edges, pdf_arcs], ignore_index=True)
    combined = combined.drop_duplicates(subset=["source_code","destination_code"]).reset_index(drop=True)
    return combined


def build_delay_stats(df_etrain):
    stats = (
        df_etrain.groupby(["station_code","station_name"])
        .agg(
            avg_delay_min        =("average_delay_minutes","mean"),
            median_delay_min     =("average_delay_minutes","median"),
            max_delay_min        =("average_delay_minutes","max"),
            std_delay_min        =("average_delay_minutes","std"),
            avg_pct_right_time   =("pct_right_time","mean"),
            avg_pct_slight_delay =("pct_slight_delay","mean"),
            avg_pct_significant  =("pct_significant_delay","mean"),
            avg_pct_cancelled    =("pct_cancelled_unknown","mean"),
            num_trains           =("train_number","nunique"),
        )
        .reset_index().round(3)
    )
    stats["delay_risk_score"] = (
        stats["avg_pct_slight_delay"]*0.3 + stats["avg_pct_significant"]*0.7
    ).clip(0,100).round(2)
    return stats.sort_values("delay_risk_score", ascending=False).reset_index(drop=True)


def build_ml_features(df_etrain):
    df = df_etrain.copy()
    df["average_delay_minutes"] = pd.to_numeric(df["average_delay_minutes"], errors="coerce").fillna(0)
    df["is_delayed"] = (df["average_delay_minutes"] > 5).astype(int)
    df["delay_category"] = pd.cut(
        df["average_delay_minutes"],
        bins=[-1, 0, 15, 60, float("inf")],
        labels=["on_time","minor_delay","moderate_delay","major_delay"]
    )
    df["is_junction"] = df["station_name"].str.contains(r"\bJN\b|\bJUNCTION\b", case=False, regex=True).astype(int)
    df["on_time_ratio"]             = df["pct_right_time"] / 100
    df["slight_delay_ratio"]        = df["pct_slight_delay"] / 100
    df["significant_delay_ratio"]   = df["pct_significant_delay"] / 100
    df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce", utc=True)
    df["scrape_month"] = df["scraped_at"].dt.month
    return df


def main():
    print("="*60)
    print("  Indian Railways — Real Data Preprocessing")
    print("  Sources: etrain_delays.csv + IRI PDF routes")
    print("="*60)

    print("\n[1/5] Loading raw data …")
    df_etrain = load_etrain_delays()
    df_pdf    = load_pdf_routes()

    print("\n[2/5] Building stations table …")
    df_stations = build_stations(df_etrain, df_pdf)
    df_stations.to_csv(os.path.join(PROC_DIR,"stations.csv"), index=False)
    df_stations[["station_name","latitude","longitude"]].to_csv(
        os.path.join(PROC_DIR,"stations_clean.csv"), index=False)
    print(f"  ✅ {len(df_stations)} stations  →  stations.csv + stations_clean.csv")

    print("\n[3/5] Building routes / graph edges …")
    df_routes = build_routes(df_etrain, df_pdf)
    df_routes.to_csv(os.path.join(PROC_DIR,"routes.csv"), index=False)
    graph_edges = df_routes[["source_station","destination_station",
                              "distance_km","travel_time_min","avg_delay_on_edge"]].rename(
        columns={"distance_km":"distance","travel_time_min":"travel_time"})
    graph_edges.to_csv(os.path.join(PROC_DIR,"graph_edges.csv"), index=False)
    print(f"  ✅ {len(df_routes)} routes  →  routes.csv + graph_edges.csv")

    print("\n[4/5] Computing delay statistics …")
    df_delay = build_delay_stats(df_etrain)
    df_delay.to_csv(os.path.join(PROC_DIR,"station_delay_stats.csv"), index=False)
    print(f"  ✅ {len(df_delay)} stations  →  station_delay_stats.csv")
    print("\n  Top 10 highest delay-risk stations:")
    print(df_delay[["station_name","avg_delay_min","delay_risk_score"]].head(10).to_string(index=False))

    print("\n[5/5] Building ML feature table …")
    df_ml = build_ml_features(df_etrain)
    df_ml.to_csv(os.path.join(PROC_DIR,"schedule_features.csv"), index=False)
    print(f"  ✅ {len(df_ml)} records  →  schedule_features.csv")

    print("\n"+"="*60)
    print("  Preprocessing complete!  →  data/processed/")
    print("="*60)
    return df_stations, df_routes, df_delay


if __name__ == "__main__":
    main()
