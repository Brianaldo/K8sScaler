import os
import yaml
import logging

from Exporter import Exporter
from Controller import Controller
from LatencyPredictorModel import LatencyPredictorModel
from MetricsFetcher import MetricsFetcher
from ResourceManager import ResourceManager
from TrafficForecasterModel import TrafficForecasterModel


class ColoredFormatter(logging.Formatter):
    COLOR_CODES = {
        logging.DEBUG: "\033[94m",     # Blue
        logging.INFO: "\033[92m",      # Green
        logging.WARNING: "\033[93m",   # Yellow
        logging.ERROR: "\033[91m",     # Red
        logging.CRITICAL: "\033[95m",  # Magenta
    }
    RESET_CODE = "\033[0m"

    def format(self, record):
        levelname = record.levelname
        log_color = self.COLOR_CODES.get(record.levelno, self.RESET_CODE)
        colored_levelname = f"{log_color}{levelname}{self.RESET_CODE}"
        record.levelname = colored_levelname
        return super().format(record)


# Set up root logger configuration
formatter = ColoredFormatter(
    '[%(asctime)s][%(levelname)s][%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)


logger = logging.getLogger('SYSTEM')
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def load_config(file_path: str):
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config


def construct_file_path(file_path: str):
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), file_path)


if __name__ == '__main__':
    logger.info("Initializing System!")
    config = load_config('config.yaml')

    exporter = Exporter(port=config['exporter']['port'])
    latency_predictor_model = LatencyPredictorModel(
        model_path=construct_file_path(
            config['modules']['latency_predictor_model']['model_path']
        ),
        num_target=config['modules']['latency_predictor_model']['num_target']
    )
    metrics_fetcher = MetricsFetcher(
        prometheus_url=config['modules']['metrics_fetcher']['prometheus_url']
    )
    resource_manager = ResourceManager()
    traffic_forecaster_model = TrafficForecasterModel(
        model_path=config['modules']['traffic_forecaster_model']['model_path']
    )

    controller = Controller(
        latency_predictor_model=latency_predictor_model,
        metrics_fetcher=metrics_fetcher,
        resource_manager=resource_manager,
        traffic_forecaster_model=traffic_forecaster_model,
        cooling_down_duration=config['modules']['controller']['cooling_down_duration'],
        max_target_pod=config['modules']['controller']['max_target_pod'],
        services_threshold=config['modules']['controller']['services'],
        exporter=exporter,
        is_test=config['modules']['controller']['test']['is_test'],
        test_data_path=config['modules']['controller']['test']['data_path'],
        test_starting_index=config['modules']['controller']['test']['starting_index']
    )

    logger.info("System is ready and running!")
    controller.run()
