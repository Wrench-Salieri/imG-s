import numpy as np
from numpy.fft import fft2, ifft2, fftshift, ifftshift
from scipy.ndimage import gaussian_filter
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim

from mri.sams import load_trace
from mri.parameters import ISS_RACK_MAX_POWER_W, ISS_RACK_MAX_VOLUME_M3, ISS_RACK_MAX_WEIGHT_KG


class SpaceMRISimulator:
    def __init__(self, ideal_phantom: np.ndarray):
        self.ideal_image = ideal_phantom.astype(np.float64)
        if self.ideal_image.max() > 1.0:
            self.ideal_image /= 255.0
        self.rows, self.cols = self.ideal_image.shape

    def forward_fft(self, img: np.ndarray) -> np.ndarray:
        return fftshift(fft2(img))

    def apply_iss_vibration_ghosting(self, kspace: np.ndarray, g_level_mg: float,
                                     vibration_freq_hz: float,
                                     calibration_factor: float) -> np.ndarray:
        """Made-up vibration: one sine wave set by the sliders."""
        if g_level_mg <= 0.0 or calibration_factor <= 0.0:
            return kspace

        corrupted_kspace = kspace.copy()
        t = np.linspace(0, 2.0, self.rows)
        amplitude = g_level_mg * calibration_factor

        phase_errors = amplitude * np.sin(2 * np.pi * vibration_freq_hz * t)
        corrupted_kspace *= np.exp(1j * phase_errors)[:, np.newaxis]
        return corrupted_kspace

    def apply_recorded_vibration(self, kspace: np.ndarray, scenario: str,
                                 calibration_factor: float,
                                 scan_time_sec: float = 2.0) -> np.ndarray:
        """Real vibration: NASA SAMS acceleration, read at the moment each k-space row is scanned."""
        if calibration_factor <= 0.0:
            return kspace

        t_sams, accel_mg = load_trace(scenario)
        t_kspace = np.linspace(0, scan_time_sec, self.rows)
        vibration_mg = np.interp(t_kspace, t_sams, accel_mg)

        corrupted_kspace = kspace.copy()
        corrupted_kspace *= np.exp(1j * vibration_mg * calibration_factor)[:, np.newaxis]
        return corrupted_kspace

    def apply_thermal_drift(self, kspace: np.ndarray, helium_pressure: float) -> np.ndarray:
        if helium_pressure >= 5.0:
            return kspace
        blur_sigma = (5.0 - helium_pressure) * 0.4
        kspace_real = gaussian_filter(kspace.real, sigma=blur_sigma)
        kspace_imag = gaussian_filter(kspace.imag, sigma=blur_sigma)
        return kspace_real + 1j * kspace_imag

    def apply_rician_noise(self, complex_image: np.ndarray, b0_tesla: float,
                           scan_averaging: int) -> np.ndarray:
        base_sigma = 0.0003 / max(b0_tesla, 0.05)
        noise_level = base_sigma / np.sqrt(max(scan_averaging, 1))

        noise_real = np.random.normal(0, noise_level, complex_image.shape)
        noise_imag = np.random.normal(0, noise_level, complex_image.shape)

        img_rician = np.sqrt((np.real(complex_image) + noise_real) ** 2 +
                             (np.imag(complex_image) + noise_imag) ** 2)
        return img_rician

    def simulate(self, b0_tesla: float = 0.15, g_level_mg: float = 30.0,
                 vibration_freq_hz: float = 5.0,
                 scan_averaging: int = 2, helium_pressure: float = 4.5,
                 vibration_calibration: float = 1.5,
                 scanner_bore_cm: float = 35.0, scanner_length_cm: float = 60.0,
                 vibration_scenario: str | None = None):
        kspace = self.forward_fft(self.ideal_image)
        if vibration_scenario:
            kspace = self.apply_recorded_vibration(kspace, vibration_scenario, vibration_calibration)
        else:
            kspace = self.apply_iss_vibration_ghosting(kspace, g_level_mg, vibration_freq_hz,
                                                       vibration_calibration)
        kspace = self.apply_thermal_drift(kspace, helium_pressure)
        complex_image = ifft2(ifftshift(kspace))
        magnitude_image = self.apply_rician_noise(complex_image, b0_tesla, scan_averaging)

        simulated_image = np.clip(magnitude_image / np.max(magnitude_image), 0, 1)

        current_ssim = ssim(self.ideal_image, simulated_image, data_range=1.0)
        current_psnr = psnr(self.ideal_image, simulated_image, data_range=1.0)

        radius_m = (scanner_bore_cm / 2.0) / 100.0
        length_m = scanner_length_cm / 100.0
        scanner_volume_m3 = np.pi * (radius_m ** 2) * length_m

        estimated_weight_kg = (40.0 + (scanner_volume_m3 * 300.0) +
                               (b0_tesla * 80.0) - (helium_pressure * 1.5))
        power_watts = (900.0 + (scanner_volume_m3 * 200.0) +
                       (g_level_mg * 10.0) + (b0_tesla * 250.0))

        iss_fit_compliant = (scanner_volume_m3 <= ISS_RACK_MAX_VOLUME_M3
                             and estimated_weight_kg <= ISS_RACK_MAX_WEIGHT_KG
                             and power_watts <= ISS_RACK_MAX_POWER_W)

        return simulated_image, {
            "SSIM": round(float(current_ssim), 4),
            "PSNR_dB": round(float(current_psnr), 2),
            "Volume_m3": round(float(scanner_volume_m3), 3),
            "Weight_kg": round(estimated_weight_kg, 1),
            "Power_W": round(power_watts, 1),
            "ISS_Rack_Compatible": iss_fit_compliant,
        }