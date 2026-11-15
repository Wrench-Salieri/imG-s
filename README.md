# Space MRI Digital Design & Simulation Engine (ISS Simulator)
# NASA Space Apps Challenge 2026 | Team:imaG-s
> *A physics-driven DSP and Digital Twin simulation engine developed for space-based MRI hardware design and live International Space Station (ISS) telemetry monitoring.*

---

## Check live demo on https://img-s-mri-designer.streamlit.app/ or run locally

## Overview
Magnetic Resonace Imaging (MRI) is crucial for monitoring astronaut health on long-duration missions (e.g., investigating Spaceflight-Associated Neuro-ocular Syndrome - SANS). However, conventional MRI scanners cannot simply be launched into space.

Space MRI Digital Design & Simulation Engine is an interacrive simulation platform that explores how MRI technology must adapt to survive spacecraft constraints. It models the intersection of medical imaging physics and aerospace engineering, allowing users to design a scanner and instantly see how space enviroments degrade the medical image.

---

## Key Features
1. **Engineering Design Mode (Manual):** Allows engineers and hardware designers to tweak custom parameters (magnetic field strength B0, helium pressure, scan averaging, and physical scanner dimensions).
2. **Mission Control Mode (Live NASA Data):** Connects with live ISS orbital tracking and telemetry APIs to dynamically inject real-time environmental interference—such as crew workouts (ARED/TRED), orbital thruster firings, and South Atlantic Anomaly (SAA) radiation spikes—directly into the MRI reconstruction pipeline.
3. **Rigorous Physical Modeling:** 
   - **K-Space Phase Shifts (g-Jitter):** Simulates structural ghosting artifacts caused by station vibrations.
   - **Rician Noise Distribution:** Models the magnitude noise inherent to low-field MRI scanners (0.05T - 0.30T).
   - **Thermal Drift:** Simulates hardware degradation due to coolant/helium pressure fluctuations.
4. **Clinical & SWaP Metrics:** Automatically evaluates image diagnostic quality using Structural Similarity Index (SSIM) and Peak Signal-to-Noise Ratio (PSNR), alongside physical size, weight, power, and ISS rack compatibility calculations.

---
## The Engineering Challenge
To operate on the International Space Station (ISS), and MRI must overcome severe limitations:
** SWaP(Size, Weight and Power): It must fit within an ISS EXPRESS Rack(max 2.0kW power, tight volume limits).
** Low Magnetic Fields(B0): To save weight and prevent interference with spacecraft navigation, space MRIs must operate at ultra-low fields(0.05T - 0.3T), drastically reducing image quality.
**Microgravity Vibrations: The ISS constantly vibrates (g-jitter) from thrusters and crew exercise, causing severe "ghosting" artifacts in scans.

## Platform Features
Our digital twin offers two primary operating modes:

1. **Engineering Design Mode: Interactively adjust hardware parameters(B0, strength, bore size, helium pressure, scan averaging). The engine calculates the estimated power/weight and renders the simulated MRI image in real-time.
   a. **Vibration Testing: Users can manually inject synthetic vibration frequencies OR select raw acceleration data from NASA's SAMS-II database (e.g., Quiet Ambient vs. Crew Exercise). This allows engineers to see exactly how real ISS mechanical disturbances cause phasae in scan.
2. **Mission Control Mode: This mode evaluates your fixed hardware design against real-time enviromental conditions. By fetching the live ISS orbital position (via external API), the system calculates simplified telemetry scenarios-such as radiation penalties when crossing the South Atlantic Anomaly-and demonstrates how dynamic space weather affects the scanner's baseline performace.

## How Does it Work? (Physics & DSP Engine)
The core of the engine is a Digital Signal Processing (DSP) pipeline that applies physics-based degradation models to a ground-truth brain phantom.

1. **K-Space Transformation MRI scanners collect data in the frequency domain. The ideal image(x,y) is transformed into K-space using a 2D Fast Fourier Transform:
   $$K(u,v) = \sum_{x=0}^{M-1} \sum_{y=0}^{N-1} I(x,y) e^{-j 2\pi \left(\frac{ux}{M} + \frac{vy}{N}\right)}$$

The project relies entirely on scientific Python libraries for signal processing, mathematical modeling, and evaluation:

* **Python 3.10+**
* **NumPy & SciPy:** For matrix operations, Fast Fourier Transforms (`numpy.fft.fft2`, `ifft2`, `fftshift`), and Gaussian filtering (`scipy.ndimage.gaussian_filter`).
* **scikit-image (`skimage.metrics`):** For calculating clinical image quality metrics (`structural_similarity` - SSIM, `peak_signal_noise_ratio` - PSNR).
* **OpenCV (`cv2`) / Pillow:** For image handling, pre-processing, and format conversion.
* **Requests:** For fetching real-time ISS telemetry and orbital tracking feeds.

## Running Locally 
Installing
```bash
git clone https://github.com/Wrench-Salieri/imG-s.git
cd imG-s
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Terminal 1: start the API

```bash
python -m uvicorn --app-dir backend api:app
```

Terminal 2: start the dashboard

```bash
python -m streamlit run app/main.py
```
📦 space-mri-simulator
 ┣ 🧠 mri_simulator.py       # Core Physics & DSP Engine (K-space, Rician noise, SWaP metrics)
 ┣ 🛰️ mission_control.py     # Live ISS Telemetry Connector (SAMS-II vibrations & SAA tracking)
 ┣ 🚀 main.py                # FastAPI / Central execution pipeline linking Design & Mission modes
 ┣ 📦 requirements.txt       # Python scientific & backend dependencies
 ┗ 📖 README.md              # Project overview, mathematical equations & setup guide
