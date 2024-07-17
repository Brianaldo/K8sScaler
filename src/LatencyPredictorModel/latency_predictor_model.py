from tensorflow.keras.models import load_model
import joblib
import pandas as pd
import numpy as np

import tensorflow as tf
tf.get_logger().setLevel('ERROR')


class LatencyPredictorModel:
    def __init__(
        self,
        model_path: str,
        num_target: int
    ):
        self.model = load_model(f"{model_path}/model.keras")
        self.pipelines = {
            'pre': joblib.load(f"{model_path}/preprocessing.joblib"),
            'post': joblib.load(f"{model_path}/postprocessing.joblib")
        }
        self.target = num_target

    def predict(
        self,
        pod: list[int],
        cpu_pod: list[int],
        rps: list[float],
        cpu_node: int,
    ):
        input_data = pd.DataFrame({
            **{f's{i}_pod': pod[i] for i in range(self.target)},
            **{f's{i}_cpu_pod': cpu_pod[i] for i in range(self.target)},
            **{f's{i}_rps': rps[i] for i in range(self.target)},
            **{f's{i}_rps_per_pod': rps[i] / pod[i] for i in range(self.target)},
            **{cpu_node: cpu_node},
        }, index=[0])

        scale_target = [
            *[f's{i}_rps' for i in range(self.target)],
            *[f's{i}_rps_per_pod' for i in range(self.target)]
        ]
        input_data[scale_target] = self.pipelines['pre'].transform(
            input_data[scale_target]
        )

        predicted_data = np.exp(
            self.pipelines['post'].inverse_transform(
                self.model.predict(
                    input_data, verbose=0
                )
            )
        )

        return {
            f's{i}': predicted_data[0][i]
            for i in range(self.target)
        }
