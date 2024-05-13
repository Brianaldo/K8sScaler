import time
import math
import traceback
import os

import numpy as np
import pandas as pd

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
rps_df_len = len(rps_df)
context_length = 1440
rps_context_df = rps_df[
    (rps_df_len - 2 * context_length):(rps_df_len - context_length)
]
rps_context = rps_context_df.to_numpy()


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
            rps = rps[np.argmax(rps[:, 0] != 0):]
            rps = np.vstack((rps_context, rps))[:1440]
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
                    forecasted_latency=lat[service][0][0],
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
    pass
