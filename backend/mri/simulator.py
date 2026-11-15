import numpy as np
from numpy.fft import fft2, ifft2, fftshift, ifftshift
from scipy.ndimage import gaussian_filter
from skimage.metrics import peak_signal_noise_ratio as psnr
from skimage.metrics import structural_similarity as ssim


class SpaceMRISimulator:
    def __init__(self, ideal_phantom: np.ndarray):
        self.ideal_image = ideal_phantom.astype(np.float64)
        if self.ideal_image.max() > 1.0:
            self.ideal_image /= 255.0
        self.rows, self.cols = self.ideal_image.shape

    def forward_fft(self, img: np.ndarray) -> np.ndarray:
        return fftshift(fft2(img))

    def apply_real_sams_vibration(self, kspace: np.ndarray, sams_csv_path: str, scan_time_sec: float = 2.0, calibration_factor: float = 1.5) -> np.ndarray: 
        # 1. Διάβασμα του αρχείου της NASA (Υποθέτουμε ότι έχει στήλες 'time' και 'y_accel')
        df = pd.read_csv(sams_csv_path, sep='\s+', comment='%', names=['time', 'x', 'y', 'z']) 

        # 2. Κανονικοποίηση του χρόνου (ξεκινάμε από το 0) 
        t_sams = df['time'].values 
        t_sams = t_sams - t_sams[0]  

        # 3. Μετατροπή της επιτάχυνσης Y σε milli-g (αν το αρχείο είναι σε g)
        y_accel_mg = df['y'].values * 1000.0 

        # 4. Χρονοδιάγραμμα του MRI (πότε διαβάζει την κάθε γραμμή του k-space) 
        t_kspace = np.linspace(0, scan_time_sec, self.rows) 

        # 5. Interpolation (Συγχρονισμός) 
        interpolator = interp1d(t_sams, y_accel_mg, kind='cubic', fill_value="extrapolate") 
        real_vibration_amplitude = interpolator(t_kspace) 

        # 6. Εφαρμογή του σφάλματος φάσης βάσει των ΠΡΑΓΜΑΤΙΚΩΝ κραδασμών 
        phase_errors = real_vibration_amplitude * calibration_factor 
        phase_shift_matrix = np.exp(1j * phase_errors) 
        corrupted_kspace = kspace.copy() 
        corrupted_kspace *= phase_shift_matrix[:, np.newaxis] 

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
                 scanner_bore_cm: float = 35.0, scanner_length_cm: float = 60.0):
        kspace = self.forward_fft(self.ideal_image)
        kspace = self.apply_real_sams_vibration(kspace, sams_csv_path="data/sams2_accel_121f08.csv", scan_time_sec=2.0) 
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

        iss_fit_compliant = scanner_volume_m3 <= 1.2 and estimated_weight_kg <= 300.0

        return simulated_image, {
            "SSIM": round(float(current_ssim), 4),
            "PSNR_dB": round(float(current_psnr), 2),
            "Volume_m3": round(float(scanner_volume_m3), 3),
            "Weight_kg": round(estimated_weight_kg, 1),
            "Power_W": round(power_watts, 1),
            "ISS_Rack_Compatible": iss_fit_compliant,
        }