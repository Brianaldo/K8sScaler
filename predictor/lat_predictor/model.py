import os

from tensorflow.keras.models import load_model
import joblib
import pandas as pd
import numpy as np

import tensorflow as tf
tf.get_logger().setLevel('ERROR')


class LatPredictor(object):

    PIPELINE = {
        'pre': joblib.load(
            os.path.join(
                os.path.dirname(__file__), "pipelines/v1/pre.joblib"
            )
        ),
        'post': joblib.load(
            os.path.join(
                os.path.dirname(__file__), "pipelines/v1/post.joblib"
            )
        )
    }

    MODEL = load_model(
        os.path.join(
            os.path.dirname(__file__), "models/v1.keras"
        )
    )

    FEATURE_COLUMN = [
        f's{i}_pod' for i in range(7)
    ] + [
        f's{i}_cpu_pod' for i in range(7)
    ] + [
        f's{i}_rps' for i in range(7)
    ] + [
        f's{i}_rps_per_pod' for i in range(7)
    ] + ['cpu_node']

    SCALE_COLUMN = [
        f's{i}_rps' for i in range(7)
    ] + [
        f's{i}_rps_per_pod' for i in range(7)
    ]

    TARGET_COLUMN = [
        f's{i}_log_lat' for i in range(7)
    ]

    @staticmethod
    def predict(
        pod: list[int],
        cpu_pod: list[int],
        rps: list[float],
        rps_per_pod: list[float],
        cpu_node: int,
    ) -> float:
        input_data = pd.DataFrame({
            **{f's{i}_pod': pod[i] for i in range(7)},
            **{f's{i}_cpu_pod': cpu_pod[i] for i in range(7)},
            **{f's{i}_rps': rps[i] for i in range(7)},
            **{f's{i}_rps_per_pod': rps_per_pod[i] for i in range(7)},
            **{cpu_node: cpu_node},
        }, index=[0])

        input_data[LatPredictor.SCALE_COLUMN] = LatPredictor.PIPELINE['pre'].transform(
            input_data[LatPredictor.SCALE_COLUMN]
        )

        predicted_data = np.exp(
            LatPredictor.PIPELINE['post'].inverse_transform(
                LatPredictor.MODEL.predict(
                    input_data, verbose=0
                )
            )
        )

        return {
            f's{i}': predicted_data[0][i]
            for i in range(7)
        }
