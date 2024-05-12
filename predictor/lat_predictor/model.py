import os

from tensorflow.keras.models import load_model
import joblib
import pandas as pd


class LatPredictor(object):
    pipeline = joblib.load(
        os.path.join(
            os.path.dirname(__file__), 'preprocessor/lat-tot-v2.joblib'
        )
    )
    model = load_model(
        os.path.join(os.path.dirname(__file__), 'model/lat-tot-v2.keras')
    )

    @staticmethod
    def predict(
        service: str,
        pod: int,
        cpu: float,
        rps: float
    ) -> float:
        preprocessed_data = LatPredictor.pipeline.transform(
            pd.DataFrame({
                'service': [service],
                'pod': [pod],
                'cpu': [cpu],
                'rps': [rps],
            })
        )

        return LatPredictor.model.predict(preprocessed_data)
