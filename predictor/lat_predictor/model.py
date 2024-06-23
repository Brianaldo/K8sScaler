import os

from tensorflow.keras.models import load_model
import joblib
import pandas as pd


class LatPredictor(object):
    PIPELINES = None
    MODELS = None

    @staticmethod
    def predict(
        service: str,
        pod: int,
        cpu_node: float,
        cpu_pod: str,
        rps: float
    ) -> float:
        input_data = pd.DataFrame({
            'pod': [pod],
            'cpu_node': [cpu_node],
            'cpu_pod': [cpu_pod],
            'rps': [rps],
            'rps_per_pod': [rps / pod]
        })

        input_data[['rps', 'rps_per_pod']] = LatPredictor.PIPELINES['pre'][service].transform(
            input_data[['rps', 'rps_per_pod']]
        )

        predicted_data = LatPredictor.MODELS[service].predict(
            input_data
        )

        return LatPredictor.PIPELINES['post'][service].inverse_transform(
            predicted_data
        )[0][0]

    @ staticmethod
    def load_preprocessor(filename: str):
        return joblib.load(
            os.path.join(
                os.path.dirname(__file__), f"pipelines/{filename}"
            )
        )

    @ staticmethod
    def load_model(filename: str):
        return load_model(
            os.path.join(
                os.path.dirname(__file__), f"models/{filename}"
            )
        )


if LatPredictor.MODELS is None:
    LatPredictor.MODELS = {
        f"s{i}": LatPredictor.load_model(f's{i}.keras')
        for i in range(7)
    }

if LatPredictor.PIPELINES is None:
    LatPredictor.PIPELINES = {
        "pre": {
            f"s{i}": LatPredictor.load_preprocessor(f'pre/s{i}.joblib')
            for i in range(7)
        },
        "post": {
            f"s{i}": LatPredictor.load_preprocessor(f'post/s{i}.joblib')
            for i in range(7)
        }
    }
