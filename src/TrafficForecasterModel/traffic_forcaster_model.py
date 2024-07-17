import logging
import torch
from transformers import PatchTSTForPrediction
import numpy as np

logger = logging.getLogger("TrafficForecasterModel")


class TrafficForecasterModel:
    def __init__(self, model_path: str):
        self.model = PatchTSTForPrediction.from_pretrained(model_path)

    def predict(self, past_values: np.ndarray) -> np.ndarray:
        outputs = self.model(
            past_values=torch.tensor(
                past_values, dtype=torch.float32
            ).unsqueeze(0)
        ).prediction_outputs
        outputs = outputs.squeeze().detach().numpy().transpose().tolist()

        logger.info(f"Forecasted Traffic: {outputs}")
        return outputs
