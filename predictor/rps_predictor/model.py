import torch
from transformers import PatchTSTForPrediction
import numpy as np


class RPSPredictor(object):
    model = PatchTSTForPrediction.from_pretrained("./model/finetune/")

    @staticmethod
    def predict(past_values: np.ndarray) -> np.ndarray:
        assert past_values.shape == (1440, 7), "Array size is not (1440, 7)"

        outputs = RPSPredictor.model(
            past_values=torch.tensor(
                past_values, dtype=torch.float32
            ).unsqueeze(0)
        ).prediction_outputs

        return outputs.squeeze().detach().numpy()
