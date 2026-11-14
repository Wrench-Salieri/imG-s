# imG-s
# 🛰️ Space MRI Digital Twin Engine (ISS Simulator)
> *A physics-driven DSP and Digital Twin simulation engine developed for space-based MRI hardware design and live International Space Station (ISS) telemetry monitoring.*

---

## 📌 Overview
Operating a Magnetic Resonance Imaging (MRI) scanner aboard the **International Space Station (ISS)** introduces extreme physical challenges: low magnetic fields ($B_0$), microgravity vibrations ($g$-jitter), thermal instability, and power/size constraints (SWaP). 

This project implements a complete **Physics & Digital Signal Processing (DSP) Engine** in Python. It bridges theoretical MRI physics (K-space manipulations, Rician noise distributions) with real-time aerospace telemetry (NASA SAMS-II acceleration data and orbital coordinates).

---

## 🚀 Key Features
1. **Engineering Design Mode (Manual):** Allows engineers and hardware designers to tweak custom parameters (magnetic field strength $B_0$, helium pressure, scan averaging, and physical scanner dimensions).
2. **Mission Control Mode (Live NASA Data):** Connects with live ISS orbital tracking and telemetry APIs to dynamically inject real-time environmental interference—such as crew workouts (ARED/TRED), orbital thruster firings, and South Atlantic Anomaly (SAA) radiation spikes—directly into the MRI reconstruction pipeline.
3. **Rigorous Physical Modeling:** 
   - **K-Space Phase Shifts ($g$-Jitter):** Simulates structural ghosting artifacts caused by station vibrations.
   - **Rician Noise Distribution:** Models the magnitude noise inherent to low-field MRI scanners ($0.05\text{T} - 0.30\text{T}$).
   - **Thermal Drift:** Simulates hardware degradation due to coolant/helium pressure fluctuations.
4. **Clinical & SWaP Metrics:** Automatically evaluates image diagnostic quality using Structural Similarity Index (SSIM) and Peak Signal-to-Noise Ratio (PSNR), alongside physical size, weight, power, and ISS rack compatibility calculations.

---

## 🛠️ Tech Stack & Dependencies

The project relies entirely on scientific Python libraries for signal processing, mathematical modeling, and evaluation:

* **Python 3.10+**
* **NumPy & SciPy:** For matrix operations, Fast Fourier Transforms (`numpy.fft.fft2`, `ifft2`, `fftshift`), and Gaussian filtering (`scipy.ndimage.gaussian_filter`).
* **scikit-image (`skimage.metrics`):** For calculating clinical image quality metrics (`structural_similarity` - SSIM, `peak_signal_noise_ratio` - PSNR).
* **OpenCV (`cv2`) / Pillow:** For image handling, pre-processing, and format conversion.
* **Requests:** For fetching real-time ISS telemetry and orbital tracking feeds.


📦 space-mri-simulator
 ┣ 🧠 mri_simulator.py       # Core Physics & DSP Engine (K-space, Rician noise, SWaP metrics)
 ┣ 🛰️ mission_control.py     # Live ISS Telemetry Connector (SAMS-II vibrations & SAA tracking)
 ┣ 🚀 main.py                # FastAPI / Central execution pipeline linking Design & Mission modes
 ┣ 📦 requirements.txt       # Python scientific & backend dependencies
 ┗ 📖 README.md              # Project overview, mathematical equations & setup guide
