
import numpy as np


def calculate_residuals(H, z, theta_hat, variances=None):
    """Calculate residuals z - H @ theta_hat and weighted statistic J."""
    H = np.asarray(H, dtype=float)
    z = np.asarray(z, dtype=float).reshape(-1)
    theta_hat = np.asarray(theta_hat, dtype=float).reshape(-1)

    if H.ndim != 2:
        raise ValueError("H must be a 2D matrix.")

    if H.shape[0] != len(z) or H.shape[1] != len(theta_hat):
        raise ValueError("Incompatible dimensions for H, z, and theta_hat.")

    residuals = z - H @ theta_hat

    if variances is None:
        weights = np.ones(len(z))
    else:
        variances = np.asarray(variances, dtype=float).reshape(-1)

        if len(variances) != len(z):
            raise ValueError("Variance count must match measurement count.")

        if not np.all(np.isfinite(variances)) or np.any(variances <= 0):
            raise ValueError("Variances must be finite and positive.")

        weights = 1.0 / variances

    statistic = float(np.sum(weights * residuals**2))

    return residuals, statistic
