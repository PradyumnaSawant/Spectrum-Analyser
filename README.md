# Spectrum-Analyser
Python-based virtual spectrometer software that analyzes spectra from live camera or images. Uses OpenCV and NumPy for intensity extraction, smoothing, and peak detection, with wavelength calibration, real-time visualization, and CSV export via a PyQt interface.
Virtual Spectrometer Software

A Python-based application for real-time analysis of light spectra using image processing and an interactive GUI.

Overview

This software processes images or live camera input to extract and analyze spectral data. It is designed to work with a DIY spectrometer setup and provides a practical way to study diffraction patterns and light intensity distribution.

Features
Live camera and static image input
Real-time intensity graph visualization
Peak detection for spectral lines
Adjustable smoothing and sensitivity
Wavelength calibration (pixel to nm mapping)
Export spectral data to CSV
Tech Stack
Python
OpenCV
NumPy and SciPy
Matplotlib
PyQt6
How It Works

The software captures a frame, extracts a horizontal strip of pixels, and computes intensity values. It applies smoothing to reduce noise, detects peaks in the spectrum, and optionally calibrates pixel positions to wavelengths for analysis.

Limitations
Accuracy depends on hardware setup and calibration
Non-linear distortions due to CD-based diffraction
Sensitive to alignment and lighting conditions
Usage
Run the Python script
Select live camera or upload an image
Adjust parameters as needed
Analyze spectrum and export data
Future Improvements
Improved calibration models
Better noise reduction techniques
