import numpy as np

# Hệ số Sinc filter
h = np.array([0.0, 0.006233, 0.02485484, 0.05332939, 0.0863577, 0.11709037,
              0.13881189, 0.14664562, 0.13881189, 0.11709037, 0.0863577,
              0.05332939, 0.02485484, 0.006233, 0.0])

# Thông số Kalman filter
Q = 0.01  # Nhiễu quá trình
R = 0.1   # Nhiễu đo lường
THRESHOLD = 5.0  # Ngưỡng phát hiện nhiễu xung (kg)
G = 9.81  # Gia tốc trọng trường (m/s²)

# Biến toàn cục để lưu trạng thái bộ lọc
filter_state = {
    'buffer': None,  # Bộ đệm Sinc filter
    'x': 0.0,       # Trạng thái Kalman (khối lượng)
    'P': 1.0        # Hiệp phương sai Kalman
}

def filter_weight(weights, accel_zs):
    global filter_state
    
    # Chuyển inputs thành mảng NumPy
    weights = np.array(weights, dtype=float)
    accel_zs = np.array(accel_zs, dtype=float)
    
    # Kiểm tra shape
    if weights.shape != accel_zs.shape:
        raise ValueError(f"Shape mismatch: weights {weights.shape}, accel_zs {accel_zs.shape}")
    
    N = len(h)  # Độ dài Sinc filter
    filtered_weights = np.zeros(len(weights))
    
    # Khởi tạo bộ đệm nếu chưa có
    if filter_state['buffer'] is None:
        filter_state['buffer'] = np.zeros(N)
    
    # Sinc filter và Kalman filter
    for i in range(len(weights)):
        # Sinc filter
        filter_state['buffer'] = np.roll(filter_state['buffer'], 1)
        filter_state['buffer'][0] = weights[i]
        sinc_out = np.sum(filter_state['buffer'] * h)
        
        # Bù gia tốc
        mass = sinc_out / (G + accel_zs[i]) if (G + accel_zs[i]) != 0 else 0.0
        
        # Kalman filter
        x_pred = filter_state['x']
        P_pred = filter_state['P'] + Q
        temp_R = R
        if abs(mass - x_pred) > THRESHOLD:
            temp_R = 10.0  # Giảm trọng số phép đo
        K = P_pred / (P_pred + temp_R)
        filter_state['x'] = x_pred + K * (mass - x_pred)
        filter_state['P'] = (1.0 - K) * P_pred
        filtered_weights[i] = filter_state['x']
    
    return filtered_weights