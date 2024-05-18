import time
import math
import traceback
import os

import numpy as np
import pandas as pd

from prometheus_client import start_http_server, Gauge

from prometheus.client import PrometheusClient
from k8s.client import K8sClient
from predictor.rps_predictor.model import RPSPredictor
from predictor.lat_predictor.model import LatPredictor

rps_df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'data/rps.csv'))
rps_df["Time"] = pd.to_datetime(rps_df['Time'], unit='ms')
rps_df.set_index("Time", inplace=True)
rps_df.sort_index(inplace=True)
rps_df.apply(pd.to_numeric)
rps_df.iloc[:, 1] = rps_df.iloc[:, 1].astype(float)

context_length = 1440
rps_context = rps_df.iloc[-2 * context_length:-context_length].to_numpy()


forecasted_rps_gauge = Gauge(
    'forecasted_rps', 'Forecasted Requests Per Second', ['service']
)
forecasted_latency_gauge = Gauge(
    'forecasted_latency', 'Forecasted Latency', ['service']
)
target_replicas_gauge = Gauge(
    'target_replicas', 'Target Replicas', ['service']
)


class Controller(object):
    INTERVAL = 60
    SERVICES = ['s0', 's1', 's2', 's3', 's4', 's5', 's6']
    LAT_THRESHOLD = {
        's0': 300,
        's1': 150,
        's2': 150,
        's3': 150,
        's4': 150,
        's5': 150,
        's6': 150
    }
    MAXIMUM_POD = 50

    @staticmethod
    def scaling_strategy(
        current_num_pod: int,
        forecasted_latency: float,
        threshold_latency: float
    ) -> int:
        return math.ceil(current_num_pod * math.floor(forecasted_latency / threshold_latency * 100) / 100)

    @ staticmethod
    def run():
        while True:
            Controller.scale()
            time.sleep(Controller.INTERVAL)

    @ staticmethod
    def scale():
        try:
            rps = PrometheusClient.fetch_workload()
            rps_len = min([len(rps[service])
                          for service in Controller.SERVICES])
            rps = np.array([
                rps[service][:min(context_length, rps_len)] for service in Controller.SERVICES
            ]).transpose()
            rps = rps[np.argmax(rps[:, 0] != 0):]
            rps = np.vstack((rps_context, rps))[-context_length:]
            forecasted_rps = {
                f's{i}': item
                for i, item
                in enumerate(RPSPredictor.predict(rps).transpose().tolist())
            }

            cpu = PrometheusClient.fetch_cpu_usage()
            pod = PrometheusClient.fetch_pod_count()
            forecasted_lat = {
                service: LatPredictor.predict(
                    service=service,
                    pod=pod.get(service),
                    cpu=cpu.get(service),
                    rps=forecasted_rps[service][0]
                ) for service in Controller.SERVICES if cpu.get(service) is not None
            }

            target_replicas = {
                service: Controller.scaling_strategy(
                    current_num_pod=pod[service],
                    forecasted_latency=forecasted_lat[service][0][0],
                    threshold_latency=Controller.LAT_THRESHOLD[service]
                ) for service in Controller.SERVICES if cpu.get(service) is not None
            }

            for service, target_replica in target_replicas.items():
                if target_replicas != pod[service]:
                    K8sClient.scale_deployment(
                        deployment_name=service,
                        replicas=min(target_replica, Controller.MAXIMUM_POD)
                    )
                    continue

            # Export to Prometheus
            for service in Controller.SERVICES:
                if forecasted_rps.get(service) is not None:
                    forecasted_rps_gauge.labels(
                        service=service
                    ).set(forecasted_rps[service][0])
                if forecasted_lat.get(service) is not None:
                    forecasted_latency_gauge.labels(
                        service=service
                    ).set(forecasted_lat[service][0][0])
                if target_replicas.get(service) is not None:
                    target_replicas_gauge.labels(
                        service=service
                    ).set(target_replicas[service])

        except Exception:
            print("[ERROR]", traceback.format_exc())


if __name__ == '__main__':
    start_http_server(8080)
    Controller.run()
