import requests

endpoints = [
    ("GET", "http://localhost:8000/api/v1/network/topology", None),
    ("GET", "http://localhost:8000/api/v1/network/critical-stations?n=5", None),
    ("GET", "http://localhost:8000/api/v1/network/delay-stats/Nagpur", None),
    ("GET", "http://localhost:8000/api/v1/network/neighbors/Nagpur", None),
    ("POST", "http://localhost:8000/api/v1/route/find", {"source": "Nagpur", "destination": "Howrah Jn"}),
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
