import sys
import numpy as np

path = sys.argv[1]
fs = 500.0                                   
d = np.fromfile(path, dtype="<f4").reshape(-1, 4).astype(float)   
t, xyz = d[:, 0], d[:, 1:]                   
xyz = xyz - xyz.mean(axis=0)                 
print(f"{len(t)} samples, {t[-1]:.1f} s")

n = int(60 * fs)                             
for i in range(0, len(xyz) - n + 1, n):
    w = xyz[i:i + n]
    rms_mg = np.sqrt((w ** 2).sum(axis=1).mean()) * 1000
    spec = sum(np.abs(np.fft.rfft(w[:, k] * np.hanning(n))) ** 2 for k in range(3))
    freq = np.fft.rfftfreq(n, 1 / fs)
    band = (freq >= 1) & (freq <= 20)
    print(f"minute {i // n}: RMS {rms_mg:.3f} milli-g, "
          f"dominant frequency 1-20 Hz: {freq[band][np.argmax(spec[band])]:.1f} Hz")