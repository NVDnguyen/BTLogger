import numpy as np

def filter_weight(data):
    """Moving average filter for Weight over 5 samples."""
    return np.mean(data[-5:]) if len(data) >= 5 else data[-1]

def filter_temperature(data):
    """Pass-through filter for Temperature (no change)."""
    return data[-1]

def filter_accel_x(data):
    """Kalman filter for Accel_X."""
    class KalmanFilter:
        def __init__(self, process_variance=1e-5, measurement_variance=0.1):
            self.x = 0
            self.P = 1
            self.Q = process_variance
            self.R = measurement_variance

        def update(self, measurement):
            self.P = self.P + self.Q
            K = self.P / (self.P + self.R)
            self.x = self.x + K * (measurement - self.x)
            self.P = (1 - K) * self.P
            return self.x

    kf = KalmanFilter()
    return kf.update(data[-1])

def filter_accel_y(data):
    """Moving average filter for Accel_Y over 5 samples."""
    return np.mean(data[-5:]) if len(data) >= 5 else data[-1]

def filter_accel_z(data):
    """Moving average filter for Accel_Z over 5 samples."""
    return np.mean(data[-5:]) if len(data) >= 5 else data[-1]