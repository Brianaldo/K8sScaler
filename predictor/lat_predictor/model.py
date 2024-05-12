from tensorflow.keras.models import load_model
import joblib
import pandas as pd


class LatPredictor(object):
    model = load_model('./model/11-05-2024-total')
    pipeline = joblib.load('./preprocessor/11-05-2024-total.joblib')

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
