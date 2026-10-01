
import numpy as np


def calculate_rmse(reference, estimated):
    """Calculate root mean squared error between reference and estimates."""
    reference = np.asarray(reference, dtype=float).reshape(-1)
    estimated = np.asarray(estimated, dtype=float).reshape(-1)

    if len(reference) != len(estimated) or len(reference) == 0:
        raise ValueError("Inputs must have the same nonzero length.")

    if not np.all(np.isfinite(reference)) or not np.all(np.isfinite(estimated)):
        raise ValueError("Inputs must contain only finite values.")

    return float(np.sqrt(np.mean((reference - estimated) ** 2)))


def binary_classification_metrics(actual, predicted):
    """Return precision, recall, F1, FPR, and confusion-matrix counts."""
    actual = np.asarray(actual, dtype=bool)
    predicted = np.asarray(predicted, dtype=bool)

    if actual.shape != predicted.shape or actual.size == 0:
        raise ValueError(
            "Actual and predicted labels must have equal nonzero shape.")

    tp = int(np.sum(actual & predicted))
    tn = int(np.sum(~actual & ~predicted))
    fp = int(np.sum(~actual & predicted))
    fn = int(np.sum(actual & ~predicted))

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )
    fpr = fp / (fp + tn) if fp + tn else 0.0

    return {
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fpr,
    }
