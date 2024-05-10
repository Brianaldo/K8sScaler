import time
import math

from prometheus.client import PrometheusClient
from k8s.client import K8sClient

class Controller(object):
    INTERVAL = 60

    def __scaling_strategy(
        current_num_pod: int,
        current_latency: float, 
        threshold_latency: float
    ) -> int:
        return math.ceil(current_num_pod * math.floor(current_latency / threshold_latency * 100) / 100)

    @staticmethod
    def run():
        while True:

            time.sleep(Controller.INTERVAL)


if __name__ == '__main__':
    Controller.run()