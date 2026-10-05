import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import model as m  # noqa: E402


def test_varsayilan_model_duragan():
    r = m.simule_et(dict(m.VARSAYILAN), "kur", 1.0, 0.5, 40)
    assert not r.tekil and r.max_kok < 1


def test_gecis_katsayisi_sifirsa_kur_soku_enflasyonu_etkilemez_eszamanli():
    p = dict(m.VARSAYILAN, gamma=0.0)
    r = m.simule_et(p, "kur", 1.0, 0.0, 10)
    assert abs(r.yol["pi"][0]) < 1e-12


def test_var_katsayilari_geri_elde_edilir():
    rng = np.random.default_rng(0)
    A1 = np.array([[0.3, 0.0, -0.1], [0.2, 0.5, 0.0], [0.1, 0.2, 0.9]])
    T = 2000
    Y = np.zeros((T, 3))
    for t in range(1, T):
        Y[t] = A1 @ Y[t - 1] + rng.standard_normal(3)
    B, *_ = m.var_tahmin(Y, 1)
    assert np.allclose(m.katsayi_matrisleri(B, 3, 1, 1)[0], A1, atol=0.06)


def test_siralama_degisince_sonuc_orijinal_duzende_doner():
    rng = np.random.default_rng(1)
    Y = rng.standard_normal((300, 3))
    a = m.var_analiz(Y, ("kur", "enf", "faiz"), 1, 6, B_sayi=20)
    b = m.var_analiz(Y, ("faiz", "enf", "kur"), 1, 6, B_sayi=20)
    # Kalıntılar neredeyse ilişkisizken sıralama etkisi küçük olmalı
    assert np.allclose(a.nokta[0], b.nokta[0], atol=0.15)
