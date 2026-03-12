import requests

endpoints = [
    ("GET", "http://localhost:8000/api/v1/network/summary", None),
    ("GET", "http://localhost:8000/api/v1/network/stations", None),
    ("GET", "http://localhost:8000/api/v1/congestion/summary", None),
    ("POST", "http://localhost:8000/api/v1/delay/predict", {
        "avg_delay_min": 45,
        "significant_delay_ratio": 0.3,
        "on_time_ratio": 0.65,
        "delay_risk_score": 35,
        "stop_number": 8,
        "betweenness_centrality": 0.1
    })
]

for method, url, data in endpoints:
    try:
        print(f"\n--- Testing {method} {url} ---")
        if method == "GET":
            response = requests.get(url)
        else:
            response = requests.post(url, json=data)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json() if response.status_code == 200 else response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")
