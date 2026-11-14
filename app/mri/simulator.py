import numpy as np


class SpaceMRISimulator:
    def __init__(self, ideal_phantom: np.ndarray):
        self.ideal_image = ideal_phantom.astype(np.float64)
        if self.ideal_image.max() > 1.0:
            self.ideal_image /= 255.0
        self.rows, self.cols = self.ideal_image.shape

    def forward_fft(self, img: np.ndarray) -> np.ndarray:
        """TODO: image -> centred k-space.   K(u, v) = FFT{ I(x, y) }, then fftshift."""
        raise NotImplementedError("forward_fft() is not written yet (app/mri/simulator.py).")

    def apply_iss_vibration_ghosting(self, kspace: np.ndarray, g_level_mg: float,
                                     vibration_freq_hz: float,
                                     calibration_factor: float) -> np.ndarray:
        """TODO: ISS vibration as a phase error on each k-space row (ghosting).

        A = g_level_mg * calibration_factor           (phase amplitude, in RADIANS)
        phi(row) = A * sin(2 * pi * f * t_row)         t_row = scan time of that row
        K_corrupted = K * exp(1j * phi)               <- note the 1j (imaginary unit)
        Broadcast the per-row phase over all columns with phase[:, np.newaxis].
        """
        raise NotImplementedError("apply_iss_vibration_ghosting() is not written yet.")

    def apply_thermal_drift(self, kspace: np.ndarray, helium_pressure: float) -> np.ndarray:
        """TODO: thermal instability as a light Gaussian blur of k-space.

        sigma_blur = (5.0 - helium_pressure) * 0.4 ; no blur at 5 bar or above.
        Filter the real and imaginary parts separately (scipy.ndimage.gaussian_filter).
        """
        raise NotImplementedError("apply_thermal_drift() is not written yet.")

    def apply_rician_noise(self, complex_image: np.ndarray, b0_tesla: float,
                           scan_averaging: int) -> np.ndarray:
        """TODO: Rician noise (Gudbjartsson and Patz, 1995).

        sigma_base  = k / max(B0, 0.05)               weaker field, more noise
        sigma_noise = sigma_base / sqrt(max(N_avg, 1))
        M = sqrt( (Re + N(0, s^2))^2 + (Im + N(0, s^2))^2 )
        """
        raise NotImplementedError("apply_rician_noise() is not written yet.")

    def simulate(self, b0_tesla: float = 0.15, g_level_mg: float = 30.0,
                 vibration_freq_hz: float = 5.0, scan_averaging: int = 2,
                 helium_pressure: float = 4.5, vibration_calibration: float = 1.5,
                 scanner_bore_cm: float = 35.0, scanner_length_cm: float = 60.0):
        """TODO: run the whole pipeline and return (simulated_image, metrics).

        simulated_image : 2D float array, same shape as the ideal image, values 0..1
        metrics         : dict with EXACTLY these keys
            "SSIM"                skimage.metrics.structural_similarity(ideal, simulated, data_range=1.0)
            "PSNR_dB"             skimage.metrics.peak_signal_noise_ratio(ideal, simulated, data_range=1.0)
            "Volume_m3"           pi * (bore_cm / 200)^2 * (length_cm / 100)
            "Weight_kg"           estimated scanner weight
            "Power_W"             estimated power consumption
            "ISS_Rack_Compatible" bool: volume <= 1.2 m^3 and weight <= 300 kg

        The parameter ranges and defaults are in parameters.py.
        """
        raise NotImplementedError("simulate() is not written yet (app/mri/simulator.py).")