import time
import math
import traceback

import numpy as np

from prometheus.client import PrometheusClient
from k8s.client import K8sClient
from predictor.rps_predictor.model import RPSPredictor
from predictor.lat_predictor.model import LatPredictor


class Controller(object):
    INTERVAL = 60
    SERVICES = ['s0', 's1', 's2', 's3', 's4', 's5', 's6']
    LAT_THRESHOLD = {
        's0': 300,
        's1': 150,
        's2': 30,
        's3': 50,
        's4': 100,
        's5': 50,
        's6': 20
    }

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
            rps = np.array([
                rps[service][:1440] for service in Controller.SERVICES
            ]).transpose()
            rps = {
                f's{i}': item
                for i, item
                in enumerate(RPSPredictor.predict(rps).transpose().tolist())
            }

            cpu = PrometheusClient.fetch_cpu_usage()
            pod = PrometheusClient.fetch_pod_count()
            lat = {
                service: LatPredictor.predict(
                    service=service,
                    pod=pod.get(service) or 1,
                    cpu=cpu.get(service) or 0,
                    rps=rps[service][0]
                ) for service in Controller.SERVICES
            }

            for service in Controller.SERVICES:
                if cpu.get(service) is None:
                    continue

                target_replicas = Controller.scaling_strategy(
                    current_num_pod=pod[service],
                    forecasted_latency=lat[service],
                    threshold_latency=Controller.LAT_THRESHOLD[service]
                )

                if target_replicas != pod[service]:
                    K8sClient.scale_deployment(
                        deployment_name=service,
                        replicas=target_replicas
                    )
        except Exception:
            print("[ERROR]", traceback.format_exc())


if __name__ == '__main__':
    Controller.run()
