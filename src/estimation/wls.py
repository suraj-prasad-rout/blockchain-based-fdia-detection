
import numpy as np


def estimate_states(H, z, variances=None):
    """
    Estimate the unknown bus phase angles using Weighted Least Squares.

    H: Measurement matrix (m x n)
    z: Measurement vector (m,)
    variances: Measurement variances (m,). If omitted, equal weights are used.

    Returns:
        theta_hat: Estimated state vector
    """
    H = np.asarray(H, dtype=float)
    z = np.asarray(z, dtype=float).reshape(-1)

    if H.ndim != 2:
        raise ValueError("H must be a 2D matrix.")

    m, n = H.shape

    if len(z) != m:
        raise ValueError("Measurement vector length must match H rows.")

    if not np.all(np.isfinite(H)) or not np.all(np.isfinite(z)):
        raise ValueError("H and z must contain only finite values.")

    if variances is None:
        weights = np.ones(m)
    else:
        variances = np.asarray(variances, dtype=float).reshape(-1)

        if len(variances) != m:
            raise ValueError("Variance count must match measurement count.")

        if not np.all(np.isfinite(variances)) or np.any(variances <= 0):
            raise ValueError("Variances must be finite and positive.")

        weights = 1.0 / variances

    if np.linalg.matrix_rank(H) < n:
        raise ValueError("System is unobservable: H lacks full column rank.")

    # Weighted least squares:
    # (H.T @ W @ H) theta = H.T @ W @ z
    # W is diagonal, so apply weights without constructing W explicitly.
    weighted_H = H * weights[:, None]
    gain = H.T @ weighted_H
    rhs = H.T @ (weights * z)

    try:
        theta_hat = np.linalg.solve(gain, rhs)
    except np.linalg.LinAlgError as exc:
        raise ValueError("WLS normal equations could not be solved.") from exc

    return theta_hat
