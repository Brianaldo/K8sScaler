import os
from pathlib import Path
import yaml

from Exporter import Exporter
from Controller import Controller
from LatencyPredictorModel import LatencyPredictorModel
from MetricsFetcher import MetricsFetcher
from ResourceManager import ResourceManager
from TrafficForecasterModel import TrafficForecasterModel


def load_config(file_path: str):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config


def construct_file_path(file_path: str):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)


if __name__ == '__main__':
    print(f"Loading config.yaml...", end="\t\t\t")
    config = load_config('config.yaml')
    print(f"✅")

    print(f"Starting Exporter...", end="\t\t\t")
    exporter = Exporter(port=config['exporter']['port'])
    print(f"✅")

    print(f"Starting LatencyPredictorModel...", end="\t")
    latency_predictor_model = LatencyPredictorModel(
        model_path=construct_file_path(
            config['modules']['latency_predictor_model']['model_path']
        ),
        num_target=config['modules']['latency_predictor_model']['num_target']
    )
    print(f"✅")

    print(f"Starting MetricsFetcher...", end="\t\t")
    metrics_fetcher = MetricsFetcher(
        prometheus_url=config['modules']['metrics_fetcher']['prometheus_url']
    )
    print(f"✅")

    print(f"Starting ResourceManager...", end="\t\t")
    resource_manager = ResourceManager()
    print(f"✅")

    print(f"Starting TrafficForecasterModel...", end="\t")
    traffic_forecaster_model = TrafficForecasterModel(
        model_path=config['modules']['traffic_forecaster_model']['model_path']
    )
    print(f"✅")

    print(f"Starting Controller...", end="\t\t\t")
    controller = Controller(
        latency_predictor_model=latency_predictor_model,
        metrics_fetcher=metrics_fetcher,
        resource_manager=resource_manager,
        traffic_forecaster_model=traffic_forecaster_model,
        cooling_down_duration=config['modules']['controller']['cooling_down_duration'],
        max_target_pod=config['modules']['controller']['max_target_pod'],
        services_threshold=config['modules']['controller']['services'],
        exporter=exporter,
        is_test=config['modules']['controller']['is_test'],
        test_data_path=config['modules']['controller']['test_data_path']
    )
    print(f"✅")

    print(f"System is running!")
    Controller.run()
