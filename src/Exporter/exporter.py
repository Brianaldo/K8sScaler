from prometheus_client import start_http_server, Gauge


class Exporter:
    def __init__(self, port=8080):
        start_http_server(port)

        self.forecasted_rps_gauge = Gauge(
            'forecasted_rps', 'Forecasted Requests Per Second', ['service']
        )
        self.predicted_latency_gauge = Gauge(
            'predicted_latency', 'Predicted Latency', ['service']
        )
        self.target_replicas_gauge = Gauge(
            'target_replicas', 'Target Replicas', ['service']
        )

    def export(
        self,
        service: str,
        forecasted_rps: float | None,
        predicted_lat: float | None,
        target_replica: int | None
    ):
        if forecasted_rps is not None:
            self.forecasted_rps_gauge.labels(
                service=service
            ).set(forecasted_rps)

        if predicted_lat is not None:
            self.predicted_latency_gauge.labels(
                service=service
            ).set(predicted_lat)

        if target_replica is not None:
            self.target_replicas_gauge.labels(
                service=service
            ).set(target_replica)
