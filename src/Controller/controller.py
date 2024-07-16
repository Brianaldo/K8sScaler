from datetime import datetime
from operator import attrgetter
import time
import math
import traceback
from typing import Dict

import numpy as np
import pandas as pd
from prometheus_api_client.utils import parse_datetime

from Exporter import Exporter
from LatencyPredictorModel import LatencyPredictorModel
from MetricsFetcher import MetricsFetcher
from ResourceManager import ResourceManager
from TrafficForecasterModel import TrafficForecasterModel


class Controller:
    def __init__(
        self,
        latency_predictor_model: LatencyPredictorModel,
        metrics_fetcher: MetricsFetcher,
        resource_manager: ResourceManager,
        traffic_forecaster_model: TrafficForecasterModel,
        cooling_down_duration: int,
        max_target_pod: int,
        services_threshold: Dict[str, int],
        exporter: None | Exporter = None,
        is_test: bool = False,
        test_data_path: None | str = None
    ):
        self.latency_predictor_model = latency_predictor_model
        self.metrics_fetcher = metrics_fetcher
        self.resource_manager = resource_manager
        self.traffic_forecaster_model = traffic_forecaster_model
        self.cooling_down_duration = cooling_down_duration
        self.max_target_pod = max_target_pod
        self.services_threshold = services_threshold
        self.services = list(services_threshold.keys())
        self.exporter = exporter

        # For testing purposes
        self.is_test = is_test
        if is_test is not None:
            self.context_length = 1440
            self.test_data = self.__prepare_test_data(test_data_path)
            self.fetch_starting_datetime = parse_datetime(
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

    def __prepare_test_data(self, test_data_path: str):
        rps_df = pd.read_csv(test_data_path)
        rps_df["Time"] = pd.to_datetime(rps_df['Time'], unit='ms')
        rps_df.set_index("Time", inplace=True)
        rps_df.sort_index(inplace=True)
        rps_df.apply(pd.to_numeric)
        rps_df.iloc[:, 1] = rps_df.iloc[:, 1].astype(float)

        rps_context = rps_df.iloc[
            -2 * self.context_length:-self.context_length
        ].to_numpy()

        return rps_context

    def __prepare_rps_data(self, rps):
        rps_len = min([len(rps[service]) for service in self.services])
        rps = np.array([
            rps[service][:min(context_length, rps_len)] for service in self.services
        ]).transpose()
        rps = rps[np.argmax(rps[:, 0] != 0):]
        rps = np.vstack((rps_context, rps))[-context_length:]

        return rps

    def scaling_strategy(
        self,
        current_num_pod: int,
        forecasted_latency: float,
        threshold_latency: float
    ) -> int:
        return math.ceil(current_num_pod * math.floor(forecasted_latency / threshold_latency * 100) / 100)

    def scale(self):
        try:
            rps, node_cpu, pod_cpu, ready_pod, pod = attrgetter(
                self.__fetch_metrics(
                    parse_datetime=self.fetch_starting_datetime
                ),
                'rps', 'node_cpu', 'pod_cpu', 'ready_pod', 'pod'
            )
            if self.is_test:
                rps = self.__prepare_rps_data(rps)

            forecasted_rps = {
                f's{i}': item
                for i, item
                in enumerate(self.traffic_forecaster_model.predict(rps).transpose().tolist())
            }

            predicted_lat = self.latency_predictor_model.predict(
                pod=[ready_pod[f's{i}'] for i in range(7)],
                cpu_pod=[pod_cpu[f's{i}'] for i in range(7)],
                rps=[forecasted_rps[f's{i}'][0] for i in range(7)],
                cpu_node=node_cpu['cpu_node']
            )

            target_replicas = {
                service: self.controller.scaling_strategy(
                    current_num_pod=ready_pod[service],
                    forecasted_latency=predicted_lat[service],
                    threshold_latency=self.services_threshold[service]
                ) if ready_pod[service] == pod[service] else pod[service]
                for service in self.services
            }

            for service, target_replica in target_replicas.items():
                if target_replicas != pod[service]:
                    self.resource_manager.scale_deployment(
                        deployment_name=service,
                        replicas=min(target_replica, self.max_target_pod)
                    )

            # Export to Prometheus
            if self.exporter:
                for service in self.controller.SERVICES:
                    self.exporter.export(
                        service=service,
                        forecasted_rps=forecasted_rps.get(service, [None])[0],
                        predicted_lat=predicted_lat.get(service),
                        target_replica=target_replicas.get(service),
                    )
        except Exception:
            print("[ERROR]", traceback.format_exc())
            time.sleep(10)

    def run(self):
        while True:
            self.controller.scale()
            time.sleep(self.cooling_down_duration)
