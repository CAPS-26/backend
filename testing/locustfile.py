from locust import HttpUser, task, between

class PM25FullAPITest(HttpUser):
    wait_time = between(1, 2)

    # Domain AOD
    @task(1)
    def get_aod_today(self):
        self.client.get("/api/v1/aod/polygon/")

    @task(1)
    def post_aod_by_date(self):
        self.client.post("/api/v1/aod/polygon/by-date/", json={"tanggal": "2025-05-10"})

    @task(1)
    def get_pm25_polygon_today(self):
        self.client.get("/api/v1/aod/pm25/polygon/")

    @task(1)
    def post_pm25_polygon_by_date(self):
        self.client.post("/api/v1/aod/pm25/polygon/by-date/", json={"tanggal": "2025-05-10"})

    # Domain Weather
    @task(1)
    def get_pm25_actual_today(self):
        self.client.get("/api/v1/weather/pm25/actual/")

    @task(1)
    def post_pm25_actual_by_date(self):
        self.client.post("/api/v1/weather/pm25/actual/by-date/", json={"date": "2025-05-10"})

    @task(1)
    def get_weather_today(self):
        self.client.get("/api/v1/weather/weather/")

    @task(1)
    def post_weather_by_date(self):
        self.client.post("/api/v1/weather/weather/by-date/", json={"date": "2025-05-17"})

    @task(1)
    def get_pm25_prediction_today(self):
        self.client.get("/api/v1/weather/pm25/prediction/")

    @task(1)
    def post_pm25_prediction_by_date(self):
        self.client.post("/api/v1/weather/pm25/prediction/by-date/", json={"date": "2025-05-17"})
