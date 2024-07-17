from prometheus_client import start_http_server, Gauge


class Exporter:
    def __init__(self, port=8080):
        start_http_server(port)

        self.forecasted_traffic_gauge = Gauge(
            'forecasted_traffic', 'Forecasted Traffic', ['service']
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
        forecasted_traffic: float | None,
        predicted_latency: float | None,
        target_replica: int | None
    ):
        if forecasted_traffic is not None:
            self.forecasted_traffic_gauge.labels(
                service=service
            ).set(forecasted_traffic)

        if predicted_latency is not None:
            self.predicted_latency_gauge.labels(
                service=service
            ).set(predicted_latency)

        if target_replica is not None:
            self.target_replicas_gauge.labels(
                service=service
            ).set(target_replica)
