import time
import math

import numpy as np

from prometheus.client import PrometheusClient
from k8s.client import K8sClient
from predictor.rps_predictor.model import RPSPredictor
from predictor.lat_predictor.model import LatPredictor


class Controller(object):
    INTERVAL = 60

    @staticmethod
    def scaling_strategy(
        current_num_pod: int,
        current_latency: float,
        threshold_latency: float
    ) -> int:
        return math.ceil(current_num_pod * math.floor(current_latency / threshold_latency * 100) / 100)

    @staticmethod
    def run():
        while True:

            time.sleep(Controller.INTERVAL)

    @staticmethod
    def test():
        print("#### PROMETHEUS ####")

        print(PrometheusClient.fetch_cpu_usage())
        print(PrometheusClient.fetch_pod_count())
        print(PrometheusClient.fetch_workload())

        print("#### KUBERNETES ####")

        print(K8sClient.get_deployment_info("s0"))

        print("#### PREDICTORS ####")

        print(RPSPredictor.predict(np.array([[0 for _ in range(7)] for _ in range(1440)])))
        print(LatPredictor.predict(service="s0", pod="1", cpu="0.5", rps="10"))


if __name__ == '__main__':
    # Controller.run()
    Controller.test()
