import os
import pandas as pd
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class SimulationService:
    def __init__(self):
        self.stations = {}
        self.train_schedules = {}  # train_number -> list of dicts: {'station': code, 'arrival': time, 'departure': time, 'lat': lat, 'lng': lng}
        self.base_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
        self.delays = {}  # train_number -> delay in minutes
        self._load_data()

    def _load_data(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        stations_csv = os.path.join(base_dir, "data", "processed", "stations.csv")
        routes_csv = os.path.join(base_dir, "data", "processed", "routes.csv")

        # Load Stations
        if os.path.exists(stations_csv):
            df_stations = pd.read_csv(stations_csv)
            for _, row in df_stations.iterrows():
                try:
                    if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
                        self.stations[str(row["station_code"])] = {
                            "name": row["station_name"],
                            "lat": float(row["latitude"]),
                            "lng": float(row["longitude"])
                        }
                except:
                    pass

        # Load Routes and Synthesize Schedule
        if os.path.exists(routes_csv):
            df_routes = pd.read_csv(routes_csv)
            # Group by train_number
            groups = df_routes.groupby("train_number")
            for train_no, group in groups:
                # Basic attempt to chain routes (assume they are in order)
                current_time = self.base_time
                schedule = []
                
                for idx, row in group.iterrows():
                    src = str(row["source_code"])
                    dst = str(row["destination_code"])
                    travel_time = row.get("travel_time_min", 60)
                    if pd.isna(travel_time) or travel_time <= 0:
                        travel_time = 60
                    
                    if not schedule:
                        # First station
                        schedule.append({
                            "station": src,
                            "arrival": current_time,
                            "departure": current_time + timedelta(minutes=5),
                            "lat": self.stations.get(src, {}).get("lat", 22.0),
                            "lng": self.stations.get(src, {}).get("lng", 80.0)
                        })
                        current_time += timedelta(minutes=5)
                    
                    current_time += timedelta(minutes=float(travel_time))
                    schedule.append({
                        "station": dst,
                        "arrival": current_time,
                        "departure": current_time + timedelta(minutes=5),
                        "lat": self.stations.get(dst, {}).get("lat", 22.0),
                        "lng": self.stations.get(dst, {}).get("lng", 80.0)
                    })
                    current_time += timedelta(minutes=5)
                
                # Check if we successfully built a schedule
                if len(schedule) > 1:
                    # Let's adjust so it loops throughout the day if we want realistic simulation
                    # We'll just store the template and use modulo logic or assume it runs daily
                    self.train_schedules[str(train_no)] = schedule

    def get_live_trains(self, sim_time_str: str = None):
        """Get positions of all trains at the given simulated time."""
        if sim_time_str:
            try:
                sim_time = datetime.fromisoformat(sim_time_str.replace('Z', '+00:00'))
                # Strip timezone for simplicity in comparison if needed, or make base_time timezone aware
                sim_time = sim_time.replace(tzinfo=None)
            except ValueError:
                sim_time = datetime.now()
        else:
            sim_time = datetime.now()

        # To keep trains on map regardless of day, we will modulo the simulation time to a single 24-hour cycle
        # Or shift base_time to match the simulated day.
        sim_time_of_day = sim_time.time()
        active_trains = []

        for train_no, schedule in self.train_schedules.items():
            delay = self.delays.get(train_no, 0)
            
            # Map schedule directly to today's date using the base_time logic
            # This is a cyclic schedule, we shift all times to be within 'sim_time' date
            start_date = sim_time.date()
            
            # Find current segment
            current_lat = schedule[0]['lat']
            current_lng = schedule[0]['lng']
            status = "Stopped"
            next_station = schedule[1]['station'] if len(schedule) > 1 else schedule[0]['station']
            
            # Since simulation time can span days, we normalize the schedule to the simulated day
            sch_start = schedule[0]['departure']
            sch_end = schedule[-1]['arrival']
            duration = sch_end - sch_start
            
            # We want to see where it is NOW.
            for i in range(len(schedule) - 1):
                st1 = schedule[i]
                st2 = schedule[i+1]
                
                # Adjust for day
                dep1 = datetime.combine(start_date, st1['departure'].time()) + timedelta(minutes=delay)
                arr2 = datetime.combine(start_date, st2['arrival'].time()) + timedelta(minutes=delay)
                
                # Handle overnight
                if arr2 < dep1:
                    arr2 += timedelta(days=1)
                
                if arr2 <= sim_time:
                    continue  # already passed
                
                if dep1 <= sim_time < arr2:
                    # In transit
                    total_time = (arr2 - dep1).total_seconds()
                    elapsed = (sim_time - dep1).total_seconds()
                    pct = elapsed / total_time if total_time > 0 else 0
                    
                    current_lat = st1['lat'] + (st2['lat'] - st1['lat']) * pct
                    current_lng = st1['lng'] + (st2['lng'] - st1['lng']) * pct
                    status = "In Transit"
                    next_station = st2['station']
                    break
                elif sim_time < dep1:
                    # Stopped at st1
                    current_lat = st1['lat']
                    current_lng = st1['lng']
                    status = f"Stopped at {st1['station']}"
                    next_station = st2['station']
                    break

            active_trains.append({
                "train_id": train_no,
                "lat": current_lat,
                "lng": current_lng,
                "status": status,
                "delay_minutes": delay,
                "next_station": next_station
            })
            
        return active_trains

    def simulate_delay(self, train_id: str, delay_minutes: int):
        current_delay = self.delays.get(train_id, 0)
        self.delays[train_id] = current_delay + delay_minutes
        
        # We can implement propagation by finding trains sharing the same next stations
        # Simplification: just return the impacted train
        impacted = [train_id]
        return {
            "message": f"Delay of {delay_minutes} minutes applied.",
            "impacted_trains": impacted
        }

simulation_service = SimulationService()
