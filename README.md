# Space MRI Digital Design & Simulation Engine (ISS Simulator)
# NASA Space Apps Challenge 2026 | Team:imaG-s
> *A physics-driven DSP and Digital Twin simulation engine developed for space-based MRI hardware design and live International Space Station (ISS) telemetry monitoring.*

---

## Check live demo on https://img-s-mri-designer.streamlit.app/ or run locally

## Overview
Magnetic Resonace Imaging (MRI) is crucial for monitoring astronaut health on long-duration missions (e.g., investigating Spaceflight-Associated Neuro-ocular Syndrome - SANS). However, conventional MRI scanners cannot simply be launched into space.

Space MRI Digital Design & Simulation Engine is an interacrive simulation platform that explores how MRI technology must adapt to survive spacecraft constraints. It models the intersection of medical imaging physics and aerospace engineering, allowing users to design a scanner and instantly see how space enviroments degrade the medical image.

---

## The Engineering Challenge
To operate on the International Space Station (ISS), and MRI must overcome severe limitations:
 * **SWaP(Size, Weight and Power)**: It must fit within an ISS EXPRESS Rack(max 2.0kW power, tight volume limits).
 * **Low Magnetic Fields(B0)**: To save weight and prevent interference with spacecraft navigation, space MRIs must operate at ultra-low fields(0.05T - 0.3T), drastically reducing image quality.
**Microgravity Vibrations: The ISS constantly vibrates (g-jitter) from thrusters and crew exercise, causing severe "ghosting" artifacts in scans.

---

## Platform Features
Our digital twin offers two primary operating modes:

1. **Engineering Design Mode**: Interactively adjust hardware parameters(B0, strength, bore size, helium pressure, scan averaging). The engine calculates the estimated power/weight and renders the simulated MRI image in real-time.
   a. **Vibration Testing**: Users can manually inject synthetic vibration frequencies OR select raw acceleration data from NASA's SAMS-II database (e.g., Quiet Ambient vs. Crew Exercise). This allows engineers to see exactly how real ISS mechanical disturbances cause phasae in scan.
2. **Mission Control Mode**: This mode evaluates your fixed hardware design against real-time enviromental conditions. By fetching the live ISS orbital position (via external API), the system calculates simplified telemetry scenarios-such as radiation penalties when crossing the South Atlantic Anomaly-and demonstrates how dynamic space weather affects the scanner's baseline performace.
   
---

## How Does it Work? (Physics & DSP Engine)
The core of the engine is a Digital Signal Processing (DSP) pipeline that applies physics-based degradation models to a ground-truth brain phantom.

1. **K-Space Transformation**: MRI scanners collect data in the frequency domain. The ideal image(x,y) is transformed into K-space using a 2D Fast Fourier Transform:
   $$S(k_x,k_y) = \iint I(x,y) e^{-i2\pi(\k_xx+k_yy} dx\,dy$$

2. **Microgravity Vibrations (Motion S\Artifacts)**: Mechanical motion during an MRI scan translates into phase shifts. Whether using a synthetic sine wave or real NASA SAMS-II telemetry, the strutural acceleration A(t) introduces a phase error Δφ(t) to the K-space lines:
   $$S_{corrupted}(k_x, k_y) = s_{ideal}9k_x,k_y) \cdot e^{i\Delta\varphi(t)}$$

3. **Low-Field Rician Noise Simulation**: Operating at low B0 fields drastically reduces the Signal-to-Noise Ration(SNR). Because MRI coils acquire complex data, the background noise follows a Rician distribution. We inject independent Gaussian noise into the real(N_R) and imaginary(N_I) channels. The noise standard deviation is inversely proportional to the magnetic field B0 and the square root of scan averages (N_avg):
   $$M_{simulated}=\sqrt{Re\{I\}+N_R(0, \sigma^2))^2 + (Im\{I\} + N_I(0, \sigma^2))^2}$$

   $$\sigma \propto \frac{1}={B_0 \sqrt{N_{avg}}}$$

4. **Systems Engineering Evaluation**: An Inverse FFT reconstructs the final image. The platform the outputs:
   * **Clinical Viability**: Evaluated via SSIM (Structural Similarity Index) and PSNR.
   * **SWaP Compliance**: Hardware volume and power formulas evaluate if the design respects the 2,000W ISS Rack limits and astronaut ergonomic fit(min. bore size).
     
---

## Tech Stack:
The project relies entirely on scientific Python libraries for signal processing, mathematical modeling, and evaluation:
   * **Core Physics**: Python 3.10+, NumPy, SciPy (FFT&DSP)
   * **Image Processing**: scikit-image(SSIM/PSNR metrics)
   * **UI & Backend**: Streamlit, FastAPI
   * **Data Integration**: Pandas, NASA SAMS-II Open Data, Open-Notify ISS API
     
--- 

## Scientific References:
 The physics engine is built upon established biomedical engineering principles

[1] 
M. Zaitsev, J. Maclaren, and M. Herbst, “Motion artifacts in MRI: A complex problem with many partial solutions,” Magnetic Resonance Imaging, vol. 42, no. 4, pp. 887–901, Oct. 2015.
[2] 
A. Van Ombergen, S. Laureys, S. Sunaert, E. Tomilovskaya, P. M. Parizel, and F. L. Wuyts, “Spaceflight-induced neuroplasticity in humans as measured by MRI: what do we know so far?,” npj Microgravity, vol. 3, no. 1, p. 2, Jan. 2017.
[3] 
G. Sarty and A. Obenaus, “Magnetic resonance imaging of astronauts on the International Space Station and into the solar system,” Canadian Aeronautics and Space Journal, vol. 58, pp. 60–68, Apr. 2012. 
[4] 
W. T. Kimberly et al., “Brain imaging with portable low-field MRI,” Nat Rev Bioeng, vol. 1, no. 9, pp. 617–630, Jul. 2023. 
[5] 
H. Gudbjartsson and S. Patz, “The rician distribution of noisy mri data,” Magnetic Resonance in Med, vol. 34, no. 6, pp. 910–914.
[6] 
L. Cui et al., “Motion artifact reduction for magnetic resonance imaging with deep learning and k-space analysis,” PLoS ONE, vol. 18, no. 1, p. e0278668, Jan. 2023.

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
