import sys
import cv2
import numpy as np
import pandas as pd
from scipy.signal import find_peaks
import matplotlib

# Set matplotlib backend to use Qt6
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QSlider, QRadioButton, 
                             QComboBox, QLineEdit, QCheckBox, QFileDialog, QMessageBox, QGroupBox, QSpinBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
import qdarktheme

class SpectrometerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🌈 Live & Static Virtual Spectrometer (PyQt6 + Dark Theme)")
        self.setGeometry(100, 100, 1200, 800)
        
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.camera_running = False
        
        self.static_image = None
        self.initUI()
        
    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Sidebar
        sidebar = QVBoxLayout()
        main_layout.addLayout(sidebar, 1) # Width ratio 1
        
        # Mode
        mode_group = QGroupBox("⚙️ Input Source")
        mode_layout = QVBoxLayout()
        self.radio_live = QRadioButton("Live Camera Feed")
        self.radio_static = QRadioButton("Static Image Upload")
        self.radio_live.setChecked(True)
        self.radio_live.toggled.connect(self.toggle_mode)
        mode_layout.addWidget(self.radio_live)
        mode_layout.addWidget(self.radio_static)
        mode_group.setLayout(mode_layout)
        sidebar.addWidget(mode_group)
        
        # Live Settings
        self.live_group = QGroupBox("Camera Connection")
        live_layout = QVBoxLayout()
        self.cam_type = QComboBox()
        self.cam_type.addItems(["📱 DroidCam WiFi (IP)", "💻 Local Webcam (USB)"])
        self.cam_type.currentIndexChanged.connect(self.update_cam_inputs)
        live_layout.addWidget(self.cam_type)
        
        self.ip_input = QLineEdit("192.168.1.5")
        self.port_input = QLineEdit("4747")
        self.index_input = QSpinBox()
        self.index_input.setRange(0, 10)
        self.index_input.setVisible(False)
        
        live_layout.addWidget(QLabel("IP Address:"))
        live_layout.addWidget(self.ip_input)
        live_layout.addWidget(QLabel("Port:"))
        live_layout.addWidget(self.port_input)
        live_layout.addWidget(self.index_input)
        
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("▶️ Start Live")
        self.btn_stop = QPushButton("⏹️ Stop Live")
        self.btn_start.clicked.connect(self.start_camera)
        self.btn_stop.clicked.connect(self.stop_camera)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        live_layout.addLayout(btn_layout)
        self.live_group.setLayout(live_layout)
        sidebar.addWidget(self.live_group)
        
        # Static Settings
        self.static_group = QGroupBox("Static Upload")
        static_layout = QVBoxLayout()
        self.btn_upload = QPushButton("Upload Image")
        self.btn_upload.clicked.connect(self.upload_image)
        static_layout.addWidget(self.btn_upload)
        self.static_group.setLayout(static_layout)
        self.static_group.setVisible(False)
        sidebar.addWidget(self.static_group)
        
        # Calibration
        calib_group = QGroupBox("📐 Wavelength Calibration")
        calib_layout = QVBoxLayout()
        self.calib_cb = QCheckBox("Enable Calibration Fit")
        calib_layout.addWidget(self.calib_cb)
        
        self.px1 = QSpinBox(); self.px1.setRange(0, 5000); self.px1.setValue(250)
        self.wav1 = QSpinBox(); self.wav1.setRange(0, 2000); self.wav1.setValue(436)
        calib_layout.addWidget(QLabel("Peak 1 (Pixel, nm):"))
        calib_layout.addWidget(self.px1); calib_layout.addWidget(self.wav1)
        
        self.px2 = QSpinBox(); self.px2.setRange(0, 5000); self.px2.setValue(550)
        self.wav2 = QSpinBox(); self.wav2.setRange(0, 2000); self.wav2.setValue(546)
        calib_layout.addWidget(QLabel("Peak 2 (Pixel, nm):"))
        calib_layout.addWidget(self.px2); calib_layout.addWidget(self.wav2)
        calib_group.setLayout(calib_layout)
        sidebar.addWidget(calib_group)
        
        # Processing
        proc_group = QGroupBox("🏔️ Signal Processing")
        proc_layout = QVBoxLayout()
        proc_layout.addWidget(QLabel("Noise Averaging (1-21):"))
        self.smooth_slider = QSlider(Qt.Orientation.Horizontal)
        self.smooth_slider.setRange(1, 21)
        self.smooth_slider.setValue(5)
        proc_layout.addWidget(self.smooth_slider)
        
        proc_layout.addWidget(QLabel("Peak Sensitivity (5-200):"))
        self.prominence_slider = QSlider(Qt.Orientation.Horizontal)
        self.prominence_slider.setRange(5, 200)
        self.prominence_slider.setValue(30)
        proc_layout.addWidget(self.prominence_slider)
        proc_group.setLayout(proc_layout)
        sidebar.addWidget(proc_group)
        
        self.btn_csv = QPushButton("💾 Export CSV")
        self.btn_csv.clicked.connect(self.export_csv)
        sidebar.addWidget(self.btn_csv)
        sidebar.addStretch()
        
        # Main View
        view_layout = QVBoxLayout()
        main_layout.addLayout(view_layout, 4) # Width ratio 4
        
        self.video_label = QLabel("Awaiting Source...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black; color: white;")
        self.video_label.setMinimumHeight(400)
        view_layout.addWidget(self.video_label)
        
        # Matplotlib Figure - Dark Theme Config
        plt.style.use('dark_background')
        self.fig, self.ax_main = plt.subplots(figsize=(7, 4))
        self.fig.patch.set_facecolor('#202124') # Fits nicely with dark theme
        self.ax_main.set_facecolor('#202124')
        self.canvas = FigureCanvas(self.fig)
        view_layout.addWidget(self.canvas)
        
        self.last_x = None
        self.last_intensity = None
        self.last_xlabel = None
        
    def update_cam_inputs(self):
        is_ip = self.cam_type.currentIndex() == 0
        self.ip_input.setVisible(is_ip)
        self.port_input.setVisible(is_ip)
        self.index_input.setVisible(not is_ip)
        
    def toggle_mode(self):
        is_live = self.radio_live.isChecked()
        self.live_group.setVisible(is_live)
        self.static_group.setVisible(not is_live)
        if not is_live:
            self.stop_camera()
            
    def start_camera(self):
        if self.cam_type.currentIndex() == 0:
            source = f"http://{self.ip_input.text()}:{self.port_input.text()}/video"
        else:
            source = self.index_input.value()
            
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            QMessageBox.critical(self, "Error", f"Cannot open source: {source}")
            return
            
        self.camera_running = True
        self.timer.start(50) # 20 fps
        
    def stop_camera(self):
        self.camera_running = False
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
            
    def upload_image(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Image Files (*.png *.jpg *.jpeg *.webp)")
        if fname:
            img = cv2.imread(fname)
            if img is not None:
                self.static_image = img
                self.analyze_frame(img)
            else:
                QMessageBox.critical(self, "Error", "Cannot read image.")
                
    def update_frame(self):
        if self.camera_running and self.cap:
            ret, frame = self.cap.read()
            if ret:
                self.analyze_frame(frame)
                
    def analyze_frame(self, frame_bgr):
        frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, c = frame.shape
        mid_row = h // 2
        
        # 1. Extract Profile
        row_data = frame[max(0, mid_row-10) : min(h, mid_row+11), :, :] 
        intensity_raw = np.mean(row_data, axis=(0, 2))
        
        # 2. Smooth
        smooth_window = max(1, self.smooth_slider.value())
        if smooth_window > 1:
            intensity = np.convolve(intensity_raw, np.ones(smooth_window)/smooth_window, mode='same')
        else:
            intensity = intensity_raw
            
        # 3. Draw Overlay
        display_frame = frame.copy()
        cv2.line(display_frame, (0, mid_row-10), (w, mid_row-10), (0, 255, 0), 2)
        cv2.line(display_frame, (0, mid_row+10), (w, mid_row+10), (0, 255, 0), 2)
        cv2.line(display_frame, (w//2, mid_row-20), (w//2, mid_row+20), (255, 0, 0), 3)
        
        # Display Image in PyQt Label
        h_d, w_d, ch = display_frame.shape
        bytes_per_line = ch * w_d
        q_img = QImage(display_frame.data, w_d, h_d, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(q_img).scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio))
        
        # 4. Calibration
        if self.calib_cb.isChecked() and self.px2.value() != self.px1.value():
            m = (self.wav2.value() - self.wav1.value()) / (self.px2.value() - self.px1.value())
            c_val = self.wav1.value() - m * self.px1.value()
            x_vals = m * np.arange(w) + c_val
            xlabel = "Wavelength (nm)"
            wave_limits = x_vals
        else:
            x_vals = np.arange(w)
            xlabel = "Pixel Position"
            wave_limits = np.linspace(400, 700, len(x_vals))
            
        self.last_x = x_vals
        self.last_intensity = intensity
        self.last_xlabel = xlabel
        
        # 5. Peaks
        peaks, _ = find_peaks(intensity, prominence=self.prominence_slider.value())
        
        # 6. Plotting
        self.ax_main.clear()
        
        self.ax_main.plot(x_vals, intensity, color='#00d2ff', linewidth=1.5) # Cyan trace
        if len(peaks) > 0:
            self.ax_main.plot(x_vals[peaks], intensity[peaks], 'rx', markersize=8)
            for p in peaks:
                self.ax_main.text(x_vals[p], intensity[p] + 8, f"{x_vals[p]:.1f}", color='#ff4b4b', fontsize=10, ha='center', weight='bold')
                
        self.ax_main.set_ylabel("Intensity", color='white')
        self.ax_main.set_xlabel(xlabel, color='white')
        self.ax_main.set_ylim(0, 300)
        self.ax_main.set_xlim(x_vals[0], x_vals[-1])
        self.ax_main.grid(True, linestyle="--", alpha=0.3)
        self.ax_main.tick_params(colors='white')
        
        self.fig.tight_layout()
        self.canvas.draw_idle()
        
    def export_csv(self):
        if self.last_x is None:
            QMessageBox.warning(self, "No Data", "No spectrum data to export.")
            return
            
        fname, _ = QFileDialog.getSaveFileName(self, "Save CSV", "spectrum.csv", "CSV Files (*.csv)")
        if fname:
            pd.DataFrame({self.last_xlabel: self.last_x, "Intensity": self.last_intensity}).to_csv(fname, index=False)
            QMessageBox.information(self, "Success", f"Data saved to {fname}")

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Apply modern dark theme
    try:
        qdarktheme.setup_theme("dark")
    except AttributeError:
        app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    
    ex = SpectrometerApp()
    ex.show()
    sys.exit(app.exec())
