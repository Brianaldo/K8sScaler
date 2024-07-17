import logging
import time
import math
from typing import Dict

import numpy as np
import pandas as pd
from prometheus_api_client.utils import parse_datetime

from Exporter import Exporter
from LatencyPredictorModel import LatencyPredictorModel
from MetricsFetcher import MetricsFetcher
from ResourceManager import ResourceManager
from TrafficForecasterModel import TrafficForecasterModel

logger = logging.getLogger("Controller")


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
            self.fetch_starting_datetime = parse_datetime("now")

    def __prepare_test_data(self, test_data_path: str):
        traffic_df = pd.read_csv(test_data_path)
        traffic_df["Time"] = pd.to_datetime(traffic_df['Time'], unit='ms')
        traffic_df.set_index("Time", inplace=True)
        traffic_df.sort_index(inplace=True)
        traffic_df.apply(pd.to_numeric)
        traffic_df.iloc[:, 1] = traffic_df.iloc[:, 1].astype(float)

        traffic_context = traffic_df.iloc[
            -2 * self.context_length:-self.context_length
        ].to_numpy()

        return traffic_context

    def __prepare_traffic_data(self, traffic):
        traffic_array = np.array([
            traffic[service] for service in self.services
        ]).T

        non_zero_indices = np.where(~np.all(traffic_array == 0, axis=1))[0]
        if non_zero_indices.size > 0:
            trimmed_append_array = traffic_array[non_zero_indices[0]:]
        else:
            trimmed_append_array = traffic_array

        return np.vstack((self.test_data, trimmed_append_array))[-self.context_length:]

    def scaling_strategy(
        self,
        current_num_pod: int,
        forecasted_latency: float,
        threshold_latency: float
    ) -> int:
        return math.ceil(current_num_pod * math.floor(forecasted_latency / threshold_latency * 100) / 100)

    def __check_metrics(self, metrics):
        def get_missing_keys(dictionary, keys):
            return [key for key in keys if key not in dictionary]

        traffic = metrics['traffic']
        node_cpu = metrics['node_cpu']
        pod_cpu = metrics['pod_cpu']
        ready_pod = metrics['ready_pod']
        pod = metrics['pod']

        if traffic is None:
            raise Exception(f"Traffic metrics are not present!")
        if node_cpu is None:
            raise Exception(f"Node CPU metrics are not present!")
        if pod_cpu is None:
            raise Exception(f"Pod CPU metrics are not present!")
        if ready_pod is None:
            raise Exception(f"Ready Pod metrics are not present!")
        if pod is None:
            raise Exception(f"Pod Count metrics are not present!")

        traffic_missing_keys = get_missing_keys(traffic, self.services)
        if len(traffic_missing_keys) > 0:
            raise Exception(
                f"Some Traffic metrics are missing: {traffic_missing_keys}.")
        pod_cpu_missing_keys = get_missing_keys(pod_cpu, self.services)
        if len(pod_cpu_missing_keys) > 0:
            raise Exception(
                f"Some Pod CPU metrics are missing: {pod_cpu_missing_keys}.")
        ready_pod_missing_keys = get_missing_keys(ready_pod, self.services)
        if len(ready_pod_missing_keys) > 0:
            raise Exception(
                f"Some Ready Pod metrics are missing: {ready_pod_missing_keys}.")
        pod_missing_keys = get_missing_keys(pod, self.services)
        if len(pod_missing_keys) > 0:
            raise Exception(
                f"Some Pod Count metrics are missing: {pod_missing_keys}.")

        return traffic, node_cpu, pod_cpu, ready_pod, pod

    def scale(self):
        metrics = self.metrics_fetcher.fetch_metrics(
            fetch_starting_datetime=self.fetch_starting_datetime
        )
        traffic, node_cpu, pod_cpu, ready_pod, pod = self.__check_metrics(
            metrics
        )

        if self.is_test:
            traffic = self.__prepare_traffic_data(traffic)

        forecasted_traffic = {
            f's{i}': item
            for i, item
            in enumerate(self.traffic_forecaster_model.predict(traffic))
        }

        predicted_lat = self.latency_predictor_model.predict(
            pod=[ready_pod[f's{i}'] for i in range(7)],
            cpu_pod=[pod_cpu[f's{i}'] for i in range(7)],
            traffic=[forecasted_traffic[f's{i}'] for i in range(7)],
            cpu_node=node_cpu['cpu_node']
        )

        target_replicas = {
            service: min(self.scaling_strategy(
                current_num_pod=ready_pod[service],
                forecasted_latency=predicted_lat[service],
                threshold_latency=self.services_threshold[service]
            ), self.max_target_pod) if ready_pod[service] == pod[service] else pod[service]
            for service in self.services
        }

        logger.info(
            f"Target Replicas: {[target_replica for _, target_replica in target_replicas.items()]}."
        )

        for service, target_replica in target_replicas.items():
            if target_replica != pod[service]:
                self.resource_manager.scale_deployment(
                    deployment_name=service,
                    replicas=target_replica
                )

        # Export to Prometheus
        if self.exporter:
            for service in self.services:
                self.exporter.export(
                    service=service,
                    forecasted_traffic=forecasted_traffic.get(service),
                    predicted_latency=predicted_lat.get(service),
                    target_replica=target_replicas.get(service),
                )

    def run(self):
        while True:
            try:
                self.scale()
                logger.info(f"Cooling down for 60 seconds.")
                time.sleep(self.cooling_down_duration)
            except Exception as e:
                logger.error(f"An error occurred: {e}")
                logger.info(f"Retrying in 10 seconds.")
                time.sleep(10)
