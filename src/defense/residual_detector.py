
import numpy as np
from scipy.stats import chi2

from src.estimation.residuals import calculate_residuals


def detect_by_residual(H, z, theta_hat, variances=None, alpha=0.05):
    """
    Detect a measurement inconsistency using a chi-square residual test.

    alpha is the significance level. For example, 0.05 corresponds
    to a 5% nominal false-alarm probability under the test assumptions.
    """
    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")

    H = np.asarray(H, dtype=float)
    m, n = H.shape
    dof = m - np.linalg.matrix_rank(H)

    if dof <= 0:
        raise ValueError("No residual degrees of freedom are available.")

    residuals, statistic = calculate_residuals(
        H, z, theta_hat, variances
    )
    threshold = float(chi2.ppf(1 - alpha, dof))

    return {
        "detected": bool(statistic > threshold),
        "statistic": statistic,
        "threshold": threshold,
        "degrees_of_freedom": int(dof),
        "residuals": residuals,
    }
