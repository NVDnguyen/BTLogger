import numpy as np

def filter_weight(weights, window_size=5):
    """
    Filter the weight data using a moving average to smooth out noise.
    
    Parameters:
    - weights: List or array of weight values (in kg).
    - window_size: Number of samples to average over (default=5).
    
    Returns:
    - smoothed: The filtered weight value for the latest sample.
    """
    if not weights:
        return 0.0
    weights = np.array(weights)
    if len(weights) < window_size:
        return np.mean(weights)
    return np.mean(weights[-window_size:])

def filter_accel(accel_xs, accel_ys, accel_zs, threshold=0.1):
    """
    Filter acceleration data using an exponential moving average with a threshold.
    
    Parameters:
    - accel_xs, accel_ys, accel_zs: Lists or arrays of acceleration values (in g).
    - threshold: Minimum change in acceleration to consider as significant (default=0.1 g).
    
    Returns:
    - xs, ys, zs: Filtered acceleration values for the latest sample.
    """
    if not accel_xs or not accel_ys or not accel_zs:
        return 0.0, 0.0, 0.0
    
    accel_xs = np.array(accel_xs)
    accel_ys = np.array(accel_ys)
    accel_zs = np.array(accel_zs)
    
    xs = accel_xs[-1]
    ys = accel_ys[-1]
    zs = accel_zs[-1]
    
    alpha = 0.2
    if len(accel_xs) >= 2:
        prev_xs = filter_accel.prev_xs if hasattr(filter_accel, 'prev_xs') else accel_xs[-2]
        prev_ys = filter_accel.prev_ys if hasattr(filter_accel, 'prev_ys') else accel_ys[-2]
        prev_zs = filter_accel.prev_zs if hasattr(filter_accel, 'prev_zs') else accel_zs[-2]
        
        if abs(accel_xs[-1] - prev_xs) > threshold:
            xs = alpha * accel_xs[-1] + (1 - alpha) * prev_xs
        else:
            xs = prev_xs
            
        if abs(accel_ys[-1] - prev_ys) > threshold:
            ys = alpha * accel_ys[-1] + (1 - alpha) * prev_ys
        else:
            ys = prev_ys
            
        if abs(accel_zs[-1] - prev_zs) > threshold:
            zs = alpha * accel_zs[-1] + (1 - alpha) * prev_zs
        else:
            zs = prev_zs
    
    filter_accel.prev_xs = xs
    filter_accel.prev_ys = ys
    filter_accel.prev_zs = zs
    
    return xs, ys, zs

filter_accel.prev_xs = 0.0
filter_accel.prev_ys = 0.0
filter_accel.prev_zs = 0.0

def filter_temperature(data):
    """Pass-through filter for temperature."""
    return data[-1] if data else 0.0

def filter_accel_x(data):
    """Wrapper for accel_x filtering."""
    xs, _, _ = filter_accel(data, [0]*len(data), [0]*len(data))
    return xs

def filter_accel_y(data):
    """Wrapper for accel_y filtering."""
    _, ys, _ = filter_accel([0]*len(data), data, [0]*len(data))
    return ys

def filter_accel_z(data):
    """Wrapper for accel_z filtering."""
    _, _, zs = filter_accel([0]*len(data), [0]*len(data), data)
    return zs