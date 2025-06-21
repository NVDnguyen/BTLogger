import asyncio
from bleak import BleakClient, BleakScanner
import struct
import csv
import os
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLineEdit, QTextEdit, QLabel, QFileDialog, QSplitter,
    QGraphicsEllipseItem, QGraphicsLineItem, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
import qasync
import pyqtgraph as pg
import numpy as np
import sys

class BluetoothDashboard(QMainWindow):
    # Signal to indicate cleanup completion
    cleanup_completed = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bluetooth Sensor Dashboard")
        self.setGeometry(100, 100, 1000, 700)

        # Initialize variables
        self.client = None
        self.devices = []
        self.characteristics = []
        self.csv_file = "sensor_data.csv"
        self.current_label = ""
        self.is_capturing = False
        self.is_connected = False
        self.data_points = []
        self.max_points = 100
        self.sample_count = 0
        self.required_samples = 100
        self.accel_plots_visible = True
        self.accel_plot_height = 300

        # Plot configuration
        self.weight_y_min = -100.0
        self.weight_y_max = 100.0
        self.accel_y_min = -4.0
        self.accel_y_max = 4.0
        self.accel_r_max = 4.0

        # Setup GUI
        self.init_ui()

        # Asyncio event loop
        self.loop = asyncio.get_event_loop()

        # Connect cleanup signal
        self.cleanup_completed.connect(self.on_cleanup_completed)

        # Apply stylesheet
        self.apply_stylesheet()

    def init_csv(self):
        """Initialize CSV file with headers."""
        if not os.path.exists(self.csv_file):
            with open(self.csv_file, mode="w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp", "Weight", "Temperature", "Accel_X", "Accel_Y", "Accel_Z", "Label"])

    def apply_stylesheet(self):
        """Apply modern stylesheet to the dashboard."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2E2E2E;
            }
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
            }
            QComboBox, QLineEdit {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
            }
            QPushButton {
                background-color: #4A4A4A;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5A5A5A;
            }
            QPushButton:disabled {
                background-color: #3A3A3A;
                color: #888888;
            }
            QPushButton#startButton {
                background-color: #28A745;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
            }
            QPushButton#startButton:hover {
                background-color: #218838;
            }
            QPushButton#startButton:disabled {
                background-color: #4A4A4A;
                color: #FFFFFF;
                border: 1px solid #555555;
            }
            QPushButton#stopButton {
                background-color: #DC3545;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 16px;
                padding: 10px;
            }
            QPushButton#stopButton:hover {
                background-color: #C82333;
            }
            QPushButton#stopButton:disabled {
                background-color: #4A4A4A;
                color: #FFFFFF;
                border: 1px solid #555555;
            }
            QPushButton#resetButton {
                background-color: #FFA500;
                color: #000000;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton#resetButton:hover {
                background-color: #FF8C00;
            }
            QTextEdit {
                background-color: #3A3A3A;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 5px;
                font-size: 14px;
            }
            QSplitter::handle {
                background-color: #555555;
            }
            QCheckBox {
                color: #FFFFFF;
                font-size: 14px;
            }
        """)

    def init_ui(self):
        """Setup the dashboard layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Control panel
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)
        control_layout.setSpacing(8)

        # Device selection
        device_layout = QHBoxLayout()
        self.device_combo = QComboBox()
        self.device_combo.addItem("Select a device...")
        device_layout.addWidget(QLabel("Bluetooth Device:"))
        device_layout.addWidget(self.device_combo)
        self.scan_button = QPushButton("Scan Devices")
        self.scan_button.clicked.connect(self.scan_devices)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_device)
        self.connect_button.setEnabled(False)
        device_layout.addWidget(self.scan_button)
        device_layout.addWidget(self.connect_button)
        control_layout.addLayout(device_layout)

        # UUID selection
        uuid_layout = QHBoxLayout()
        self.uuid_combo = QComboBox()
        self.uuid_combo.addItem("Select a UUID...")
        self.uuid_combo.setEditable(True)
        self.uuid_combo.setInsertPolicy(QComboBox.NoInsert)
        uuid_layout.addWidget(QLabel("Characteristic UUID:"))
        uuid_layout.addWidget(self.uuid_combo)
        self.discover_button = QPushButton("Discover UUIDs")
        self.discover_button.clicked.connect(self.discover_characteristics)
        self.discover_button.setEnabled(False)
        uuid_layout.addWidget(self.discover_button)
        control_layout.addLayout(uuid_layout)

        # CSV file selection
        csv_layout = QHBoxLayout()
        self.csv_input = QLineEdit(self.csv_file)
        self.csv_input.setPlaceholderText("Enter or select CSV file")
        csv_layout.addWidget(QLabel("CSV File:"))
        csv_layout.addWidget(self.csv_input)
        self.csv_button = QPushButton("Browse")
        self.csv_button.clicked.connect(self.select_csv_file)
        csv_layout.addWidget(self.csv_button)
        control_layout.addLayout(csv_layout)

        # Label and sample count input
        label_sample_layout = QHBoxLayout()
        self.label_input = QLineEdit()
        self.label_input.setPlaceholderText("Enter session label")
        label_sample_layout.addWidget(QLabel("Session Label:"))
        label_sample_layout.addWidget(self.label_input)
        self.sample_input = QLineEdit(str(self.required_samples))
        self.sample_input.setPlaceholderText("Number of samples")
        label_sample_layout.addWidget(QLabel("Samples:"))
        label_sample_layout.addWidget(self.sample_input)
        control_layout.addLayout(label_sample_layout)

        # Start/Stop/Reset buttons
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Capture")
        self.start_button.setObjectName("startButton")
        self.start_button.clicked.connect(self.start_capture)
        self.start_button.setEnabled(False)
        self.stop_button = QPushButton("Stop Capture")
        self.stop_button.setObjectName("stopButton")
        self.stop_button.clicked.connect(self.stop_capture)
        self.stop_button.setEnabled(False)
        self.reset_button = QPushButton("Reset")
        self.reset_button.setObjectName("resetButton")
        self.reset_button.clicked.connect(self.reset_app)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.reset_button)
        control_layout.addLayout(button_layout)

        main_layout.addWidget(control_widget)

        # Plot configuration
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        config_layout.setSpacing(8)

        # Weight/Temperature plot range
        weight_config_layout = QHBoxLayout()
        self.weight_y_min_input = QLineEdit(str(self.weight_y_min))
        self.weight_y_max_input = QLineEdit(str(self.weight_y_max))
        self.weight_y_min_input.setPlaceholderText("Y Min")
        self.weight_y_max_input.setPlaceholderText("Y Max")
        self.apply_weight_range_button = QPushButton("Apply Weight/Temp Range")
        self.apply_weight_range_button.clicked.connect(self.apply_weight_plot_range)
        weight_config_layout.addWidget(QLabel("Weight/Temp Plot Y-Range:"))
        weight_config_layout.addWidget(self.weight_y_min_input)
        weight_config_layout.addWidget(self.weight_y_max_input)
        weight_config_layout.addWidget(self.apply_weight_range_button)
        config_layout.addLayout(weight_config_layout)

        # Acceleration plot range
        accel_config_layout = QHBoxLayout()
        self.accel_y_min_input = QLineEdit(str(self.accel_y_min))
        self.accel_y_max_input = QLineEdit(str(self.accel_y_max))
        self.accel_y_min_input.setPlaceholderText("Y Min")
        self.accel_y_max_input.setPlaceholderText("Y Max")
        self.apply_accel_range_button = QPushButton("Apply Accel Line Range")
        self.apply_accel_range_button.clicked.connect(self.apply_accel_line_range)
        accel_config_layout.addWidget(QLabel("Accel Line Plot Y-Range:"))
        accel_config_layout.addWidget(self.accel_y_min_input)
        accel_config_layout.addWidget(self.accel_y_max_input)
        accel_config_layout.addWidget(self.apply_accel_range_button)
        config_layout.addLayout(accel_config_layout)

        # Acceleration polar plot range
        polar_config_layout = QHBoxLayout()
        self.accel_r_max_input = QLineEdit(str(self.accel_r_max))
        self.accel_r_max_input.setPlaceholderText("Max Radius")
        self.apply_polar_range_button = QPushButton("Apply Polar Range")
        self.apply_polar_range_button.clicked.connect(self.apply_polar_plot_range)
        polar_config_layout.addWidget(QLabel("Accel Polar Plot Max Radius:"))
        polar_config_layout.addWidget(self.accel_r_max_input)
        polar_config_layout.addWidget(self.apply_polar_range_button)
        config_layout.addLayout(polar_config_layout)

        # Acceleration plot height and visibility
        accel_display_layout = QHBoxLayout()
        self.accel_height_input = QLineEdit(str(self.accel_plot_height))
        self.accel_height_input.setPlaceholderText("Height (px)")
        self.apply_height_button = QPushButton("Apply Accel Plot Height")
        self.apply_height_button.clicked.connect(self.apply_accel_plot_height)
        self.show_accel_checkbox = QCheckBox("Show Acceleration Plots")
        self.show_accel_checkbox.setChecked(True)
        self.show_accel_checkbox.stateChanged.connect(self.toggle_accel_plots)
        accel_display_layout.addWidget(QLabel("Accel Plot Height:"))
        accel_display_layout.addWidget(self.accel_height_input)
        accel_display_layout.addWidget(self.apply_height_button)
        accel_display_layout.addWidget(self.show_accel_checkbox)
        config_layout.addLayout(accel_display_layout)

        main_layout.addWidget(config_widget)

        # Log and Plot splitter
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(100)
        splitter.addWidget(self.log_text)

        # Plot container
        plot_widget = QWidget()
        self.plot_layout = QVBoxLayout(plot_widget)
        self.plot_layout.setSpacing(10)
        splitter.addWidget(plot_widget)

        # Weight/Temperature plot
        self.weight_plot = pg.PlotWidget()
        self.weight_plot.setTitle("Weight and Temperature", color='w', size='12pt')
        self.weight_plot.setLabel('left', 'Value', color='w')
        self.weight_plot.setLabel('bottom', 'Time (s)', color='w')
        self.weight_plot.addLegend()
        self.weight_plot.showGrid(x=True, y=True)
        self.weight_plot.setBackground('k')
        self.plot_layout.addWidget(self.weight_plot)

        # Acceleration plots (polar + line)
        self.accel_plot_layout = QHBoxLayout()
        self.plot_layout.addLayout(self.accel_plot_layout)

        # Acceleration polar plot
        self.accel_polar_plot = pg.PlotWidget()
        self.accel_polar_plot.setTitle("Acceleration Vector", color='w', size='12pt')
        self.accel_polar_plot.setAspectLocked(True)
        self.accel_polar_plot.setLabel('left', 'Y (g)', color='w')
        self.accel_polar_plot.setLabel('bottom', 'X (g)', color='w')
        self.accel_polar_plot.addLegend()
        self.accel_polar_plot.setBackground('k')
        self.accel_polar_plot.setFixedSize(self.accel_plot_height, self.accel_plot_height)
        self.accel_plot_layout.addWidget(self.accel_polar_plot)

        # Acceleration line plot
        self.accel_line_plot = pg.PlotWidget()
        self.accel_line_plot.setTitle("Acceleration Over Time", color='w', size='12pt')
        self.accel_line_plot.setLabel('left', 'Acceleration (g)', color='w')
        self.accel_line_plot.setLabel('bottom', 'Time (s)', color='w')
        self.accel_line_plot.addLegend()
        self.accel_line_plot.showGrid(x=True, y=True)
        self.accel_line_plot.setBackground('k')
        self.accel_plot_layout.addWidget(self.accel_line_plot)

        # Initialize plot curves
        self.weight_curve = self.weight_plot.plot(pen='r', name='Weight')
        self.temp_curve = self.weight_plot.plot(pen='g', name='Temperature')
        self.accel_scatter = self.accel_polar_plot.plot(
            symbol='o', symbolSize=10, symbolPen=None, name='Accel Vector'
        )
        self.accel_x_curve = self.accel_line_plot.plot(pen='b', name='Accel_X')
        self.accel_y_curve = self.accel_line_plot.plot(pen='y', name='Accel_Y')
        self.accel_z_curve = self.accel_line_plot.plot(pen='c', name='Accel_Z')

        # Add polar grid
        self.add_polar_grid()

        # Set initial splitter sizes
        splitter.setSizes([150, 550])

        # Enable Connect button when a device is selected
        self.device_combo.currentIndexChanged.connect(self.update_connect_button)

    def add_polar_grid(self):
        """Add polar grid to the acceleration polar plot."""
        self.accel_polar_plot.setXRange(-self.accel_r_max, self.accel_r_max)
        self.accel_polar_plot.setYRange(-self.accel_r_max, self.accel_r_max)
        for r in [1, 2, 3, 4]:
            circle = QGraphicsEllipseItem(-r, -r, 2*r, 2*r)
            circle.setPen(pg.mkPen('w', style=Qt.DashLine))
            self.accel_polar_plot.addItem(circle)
        for angle in range(0, 360, 45):
            theta = np.radians(angle)
            x = self.accel_r_max * np.cos(theta)
            y = self.accel_r_max * np.sin(theta)
            line = QGraphicsLineItem(0, 0, x, y)
            line.setPen(pg.mkPen('w', style=Qt.DashLine))
            self.accel_polar_plot.addItem(line)

    def log(self, message):
        """Append message to the log display."""
        self.log_text.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {message}")

    def update_connect_button(self):
        """Enable Connect button when a valid device is selected."""
        self.connect_button.setEnabled(self.device_combo.currentIndex() > 0 and not self.is_connected)

    def select_csv_file(self):
        """Open file dialog to select CSV file."""
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Select CSV File", self.csv_file, "CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            if not file_name.endswith(".csv"):
                file_name += ".csv"
            self.csv_file = file_name
            self.csv_input.setText(file_name)
            self.init_csv()
            self.log(f"Selected CSV file: {file_name}")

    def apply_weight_plot_range(self):
        """Apply y-axis range to Weight/Temperature plot."""
        try:
            y_min = float(self.weight_y_min_input.text())
            y_max = float(self.weight_y_max_input.text())
            if y_min >= y_max:
                self.log("Error: Weight/Temp Y Min must be less than Y Max.")
                return
            self.weight_y_min = y_min
            self.weight_y_max = y_max
            self.weight_plot.setYRange(y_min, y_max)
            self.log(f"Weight/Temp plot range updated: Y Min = {y_min}, Y Max = {y_max}")
        except ValueError:
            self.log("Error: Invalid Weight/Temp Y-axis range values.")

    def apply_accel_line_range(self):
        """Apply y-axis range to Acceleration line plot."""
        try:
            y_min = float(self.accel_y_min_input.text())
            y_max = float(self.accel_y_max_input.text())
            if y_min >= y_max:
                self.log("Error: Accel Line Y Min must be less than Y Max.")
                return
            self.accel_y_min = y_min
            self.accel_y_max = y_max
            self.accel_line_plot.setYRange(y_min, y_max)
            self.log(f"Accel line plot range updated: Y Min = {y_min}, Y Max = {y_max}")
        except ValueError:
            self.log("Error: Invalid Accel Line Y-axis range values.")

    def apply_polar_plot_range(self):
        """Apply max radius to Acceleration polar plot."""
        try:
            r_max = float(self.accel_r_max_input.text())
            if r_max <= 0:
                self.log("Error: Accel Max Radius must be positive.")
                return
            self.accel_r_max = r_max
            self.accel_polar_plot.setXRange(-r_max, r_max)
            self.accel_polar_plot.setYRange(-r_max, r_max)
            self.accel_polar_plot.clear()
            self.accel_scatter = self.accel_polar_plot.plot(
                symbol='o', symbolSize=10, symbolPen=None, name='Accel Vector'
            )
            self.add_polar_grid()
            self.log(f"Accel polar plot max radius updated: {r_max}")
        except ValueError:
            self.log("Error: Invalid Accel Max Radius value.")

    def apply_accel_plot_height(self):
        """Apply height to acceleration plots."""
        try:
            height = int(self.accel_height_input.text())
            if not (100 <= height <= 1000):
                self.log("Error: Accel plot height must be between 100 and 1000 pixels.")
                return
            self.accel_plot_height = height
            self.accel_polar_plot.setFixedSize(height, height)
            self.accel_line_plot.setMinimumHeight(height)
            self.log(f"Acceleration plots height updated to {height} pixels.")
        except ValueError:
            self.log("Error: Invalid accel plot height value. Please enter a number.")

    def toggle_accel_plots(self, state):
        """Show or hide acceleration plots based on checkbox state."""
        self.accel_plots_visible = state == Qt.Checked
        for i in range(self.accel_plot_layout.count()):
            widget = self.accel_plot_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(self.accel_plots_visible)
        self.log(f"Acceleration plots {'shown' if self.accel_plots_visible else 'hidden'}.")

    async def cleanup(self):
        """Helper method to stop capture and disconnect client with timeout."""
        self.log("Starting cleanup process...")
        try:
            if self.is_capturing:
                try:
                    await asyncio.wait_for(self.stop_capture(), timeout=5.0)
                    self.log("Capture stopped successfully.")
                except asyncio.TimeoutError:
                    self.log("Timeout stopping capture. Forcing stop.")
                    self.is_capturing = False
                    self.start_button.setEnabled(self.is_connected)
                    self.stop_button.setEnabled(False)

            if self.client and self.client.is_connected:
                try:
                    await asyncio.wait_for(self.client.disconnect(), timeout=5.0)
                    self.log("Disconnected from device successfully.")
                except asyncio.TimeoutError:
                    self.log("Timeout disconnecting device. Forcing disconnect.")
                finally:
                    self.is_connected = False
                    self.client = None
        except Exception as e:
            self.log(f"Cleanup error: {e}")
            self.is_connected = False
            self.client = None
            raise
        finally:
            self.log("Cleanup process completed.")

    @qasync.asyncSlot(bool, str)
    def on_cleanup_completed(self, success, error_message):
        """Handle completion of cleanup process."""
        if not success:
            self.log(f"Cleanup failed: {error_message}")
        self.complete_reset()

    def complete_reset(self):
        """Finalize reset after cleanup."""
        self.data_points.clear()
        self.sample_count = 0
        self.device_combo.setCurrentIndex(0)
        self.uuid_combo.setCurrentIndex(0)
        self.csv_input.setText("sensor_data.csv")
        self.label_input.clear()
        self.sample_input.setText(str(100))
        self.required_samples = 100
        self.weight_y_min_input.setText(str(-100.0))
        self.weight_y_max_input.setText(str(100.0))
        self.accel_y_min_input.setText(str(-4.0))
        self.accel_y_max_input.setText(str(4.0))
        self.accel_r_max_input.setText(str(4.0))
        self.accel_height_input.setText(str(300))
        self.accel_plot_height = 300
        self.accel_polar_plot.setFixedSize(300, 300)
        self.accel_line_plot.setMinimumHeight(300)
        self.show_accel_checkbox.setChecked(True)
        self.toggle_accel_plots(Qt.Checked)
        self.weight_curve.setData([], [])
        self.temp_curve.setData([], [])
        self.accel_scatter.setData([], [])
        self.accel_x_curve.setData([], [])
        self.accel_y_curve.setData([], [])
        self.accel_z_curve.setData([], [])
        self.weight_plot.setYRange(-100.0, 100.0)
        self.accel_line_plot.setYRange(-4.0, 4.0)
        self.accel_polar_plot.setXRange(-4.0, 4.0)
        self.accel_polar_plot.setYRange(-4.0, 4.0)
        self.accel_polar_plot.clear()
        self.accel_scatter = self.accel_polar_plot.plot(
            symbol='o', symbolSize=10, symbolPen=None, name='Accel Vector'
        )
        self.add_polar_grid()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.discover_button.setEnabled(False)
        self.connect_button.setEnabled(self.device_combo.currentIndex() > 0)
        self.log("Application reset to initial state.")
        self.reset_button.setEnabled(True)  # Re-enable reset button

    @qasync.asyncSlot()
    async def perform_cleanup(self):
        """Run cleanup asynchronously and emit completion signal."""
        try:
            await self.cleanup()
            self.cleanup_completed.emit(True, "")
        except Exception as e:
            self.cleanup_completed.emit(False, str(e))

    def reset_app(self):
        """Reset the application to initial state."""
        self.reset_button.setEnabled(False)  # Disable reset button during operation
        self.log("Initiating reset...")
        if self.is_capturing or self.is_connected:
            # Schedule cleanup asynchronously
            asyncio.run_coroutine_threadsafe(self.perform_cleanup(), self.loop)
        else:
            self.complete_reset()

    def update_plot(self, sensor_data):
        """Update the real-time plots with new sensor data."""
        if not self.is_capturing:
            return
        timestamp = datetime.now().timestamp()
        accel_x = sensor_data["acceleration"][0]
        accel_y = sensor_data["acceleration"][1]
        accel_z = sensor_data["acceleration"][2]

        self.data_points.append({
            "time": timestamp,
            "weight": sensor_data["weight"],
            "temperature": sensor_data["temperature"],
            "accel_x": accel_x,
            "accel_y": accel_y,
            "accel_z": accel_z
        })

        if len(self.data_points) > self.max_points:
            self.data_points.pop(0)

        times = [dp["time"] - self.data_points[0]["time"] for dp in self.data_points]
        weights = [dp["weight"] for dp in self.data_points]
        temps = [dp["temperature"] for dp in self.data_points]
        accel_xs = [dp["accel_x"] for dp in self.data_points]
        accel_ys = [dp["accel_y"] for dp in self.data_points]
        accel_zs = [dp["accel_z"] for dp in self.data_points]

        self.weight_curve.setData(times, weights)
        self.temp_curve.setData(times, temps)

        if self.accel_plots_visible:
            self.accel_x_curve.setData(times, accel_xs)
            self.accel_y_curve.setData(times, accel_ys)
            self.accel_z_curve.setData(times, accel_zs)
            if accel_xs:
                z = accel_zs[-1]
                color = pg.mkBrush((255, max(0, min(255, int(128 + z * 32))), 0))
                self.accel_scatter.setData([accel_xs[-1]], [accel_ys[-1]], symbolBrush=color)

    def decode_sensor_data(self, data):
        """Decode sensor data from the characteristic with enhanced error handling."""
        try:
            if len(data) != 20:
                return None, f"Invalid data length: {len(data)} bytes, expected 20. Raw data: {data.hex()}"
            weight, temp, accel_x, accel_y, accel_z = struct.unpack("<Iffff", data)

            if weight == 4294967295:
                return None, f"Invalid weight: error code 0xFFFFFFFF. Raw data: {data.hex()}"

            
            temp_min, temp_max = 0.0, 85.0
            accel_min, accel_max = -8.0, 8.0
            if not (temp_min <= temp <= temp_max):
                return None, f"Temperature out of range: {temp} (expected {temp_min}-{temp_max}). Raw data: {data.hex()}"
            if not (accel_min <= accel_x <= accel_max and
                    accel_min <= accel_y <= accel_max and
                    accel_min <= accel_z <= accel_max):
                return None, f"Acceleration out of range: ({accel_x}, {accel_y}, {accel_z}) (expected {accel_min}-{accel_max}). Raw data: {data.hex()}"

            return {
                "weight": weight,
                "temperature": temp,
                "acceleration": (accel_x, accel_y, accel_z)
            }, None
        except struct.error as e:
            return None, f"Struct unpacking error: {e}. Raw data: {data.hex()}"
        except Exception as e:
            return None, f"Failed to decode sensor data: {e}. Raw data: {data.hex()}"

    async def notification_handler(self, sender, data):
        """Handle incoming sensor data, save to CSV, and update plots."""
        sensor_data, error = self.decode_sensor_data(data)
        if error:
            self.log(f"Error decoding sensor data: {error}")
            return

        if self.is_capturing:
            self.sample_count += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.csv_file, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([
                    timestamp,
                    sensor_data["weight"],
                    sensor_data["temperature"],
                    sensor_data["acceleration"][0],
                    sensor_data["acceleration"][1],
                    sensor_data["acceleration"][2],
                    self.current_label
                ])
            self.update_plot(sensor_data)

            if self.sample_count >= self.required_samples:
                self.log(f"Session completed with {self.sample_count} samples.")
                await self.stop_capture()

    @qasync.asyncSlot()
    async def scan_devices(self):
        """Scan for Bluetooth devices."""
        self.scan_button.setEnabled(False)
        self.log("Scanning for devices...")
        self.device_combo.clear()
        self.device_combo.addItem("Select a device...")
        self.devices = []

        try:
            devices = await BleakScanner.discover(timeout=5.0)
            for device in devices:
                if device.name:
                    self.devices.append(device)
                    self.device_combo.addItem(f"{device.name} ({device.address})")
            self.log(f"Found {len(self.devices)} devices.")
        except Exception as e:
            self.log(f"Scan error: {e}")
        finally:
            self.scan_button.setEnabled(True)

    @qasync.asyncSlot()
    async def connect_device(self):
        """Connect to the selected device."""
        if self.is_connected:
            self.log("Already connected to a device.")
            return

        device_index = self.device_combo.currentIndex() - 1
        if device_index < 0:
            self.log("Please select a device.")
            return

        device = self.devices[device_index]
        self.connect_button.setEnabled(False)
        self.log(f"Connecting to {device.name} ({device.address})...")

        try:
            self.client = BleakClient(device)
            await self.client.connect()
            self.is_connected = True
            self.log(f"Connected to {device.name} ({device.address})")
            self.discover_button.setEnabled(True)
            self.start_button.setEnabled(True)
        except Exception as e:
            self.log(f"Connection error: {e}")
            self.client = None
            self.is_connected = False
        finally:
            self.connect_button.setEnabled(self.device_combo.currentIndex() > 0 and not self.is_connected)

    @qasync.asyncSlot()
    async def discover_characteristics(self):
        """Discover characteristics of the connected device."""
        if not self.client or not self.client.is_connected:
            self.log("Not connected to a device. Please connect first.")
            return

        self.discover_button.setEnabled(False)
        self.log("Discovering characteristics...")
        self.uuid_combo.clear()
        self.uuid_combo.addItem("Select a UUID...")
        self.characteristics = []

        try:
            services = await self.client.get_services()
            for service in services:
                for char in service.characteristics:
                    if "notify" in char.properties:
                        self.characteristics.append(char)
                        self.uuid_combo.addItem(f"{char.uuid} ({char.description or 'No description'})")
            self.log(f"Found {len(self.characteristics)} characteristics with notification support.")
        except Exception as e:
            self.log(f"Discovery error: {e}")
        finally:
            self.discover_button.setEnabled(True)

    @qasync.asyncSlot()
    async def start_capture(self):
        """Start capturing data from the selected UUID."""
        if self.is_capturing:
            self.log("Capture already in progress.")
            return

        if not self.is_connected or not self.client:
            self.log("Not connected to a device. Please connect first.")
            return

        uuid_index = self.uuid_combo.currentIndex() - 1
        if uuid_index < 0:
            uuid = self.uuid_combo.currentText().strip()
        else:
            uuid = self.characteristics[uuid_index].uuid

        if not uuid:
            self.log("Please select or enter a valid UUID.")
            return

        try:
            required_samples = int(self.sample_input.text())
            if required_samples <= 0:
                self.log("Error: Number of samples must be positive.")
                return
            self.required_samples = required_samples
        except ValueError:
            self.log("Error: Invalid number of samples. Please enter a positive integer.")
            return

        self.current_label = self.label_input.text().strip() or "No Label"
        if not self.csv_file:
            self.log("Please select a CSV file.")
            return
        self.init_csv()
        self.data_points.clear()
        self.sample_count = 0
        self.weight_plot.setYRange(self.weight_y_min, self.weight_y_max)
        if self.accel_plots_visible:
            self.accel_line_plot.setYRange(self.accel_y_min, self.accel_y_max)
            self.accel_polar_plot.setXRange(-self.accel_r_max, self.accel_r_max)
            self.accel_polar_plot.setYRange(-self.accel_r_max, self.accel_r_max)
            self.accel_polar_plot.clear()
            self.accel_scatter = self.accel_polar_plot.plot(
                symbol='o', symbolSize=10, symbolPen=None, name='Accel Vector'
            )
            self.add_polar_grid()

        try:
            await self.client.start_notify(uuid, self.notification_handler)
            self.log(f"Notifications enabled for UUID {uuid}. Collecting {self.required_samples} samples.")
            self.is_capturing = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        except Exception as e:
            self.log(f"Error starting notifications: {e}")

    @qasync.asyncSlot()
    async def stop_capture(self):
        """Pause capturing data without disconnecting the device."""
        if not self.is_capturing:
            self.log("No active capture to stop.")
            return

        try:
            uuid_index = self.uuid_combo.currentIndex() - 1
            uuid = self.characteristics[uuid_index].uuid if uuid_index >= 0 else self.uuid_combo.currentText().strip()
            await self.client.stop_notify(uuid)
            self.log(f"Data capture paused for UUID {uuid}. Collected {self.sample_count} samples.")
            self.is_capturing = False
            self.start_button.setEnabled(self.is_connected)
            self.stop_button.setEnabled(False)
        except Exception as e:
            self.log(f"Error stopping capture: {e}")

    def closeEvent(self, event):
        """Ensure cleanup on window close."""
        if self.client and self.client.is_connected:
            try:
                asyncio.run_coroutine_threadsafe(self.cleanup(), self.loop).result(timeout=5.0)
            except Exception as e:
                self.log(f"Error during window close cleanup: {e}")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = BluetoothDashboard()
    window.show()

    with loop:
        loop.run_forever()