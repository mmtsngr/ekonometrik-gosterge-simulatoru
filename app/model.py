"""
Ekonometrik Gösterge Simülatörü — hesaplama çekirdeği.

İki bölüm:
  1) Kalibre edilmiş küçük açık ekonomi modeli (geriye dönük, Rudebusch-Svensson tipi)
  2) Türkiye verisiyle indirgenmiş VAR(p), Cholesky tanımlaması, bootstrap güven bantları

Yalnızca numpy kullanır; böylece Shinylive (tarayıcıda Pyodide) içinde hızlı çalışır.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# 1) KALİBRE MODEL
# ---------------------------------------------------------------------------
#   Çıktı açığı : y_t  = ρy·y_{t-1} − σ·(i_{t-1} − π_{t-1}) + δ·q_{t-1} + ε^y_t
#   Enflasyon   : π_t  = ρπ·π_{t-1} + κ·y_{t-1} + γ·Δe_t + ε^π_t       (γ: kur geçişkenliği)
#   Politika    : i_t  = ρi·i_{t-1} + (1−ρi)(φπ·π_t + φy·y_t) + ε^i_t   (Taylor kuralı)
#   Nominal kur : Δe_t = −θ·(i_t − π_t) + ε^e_t                          (basit UIP / risk primi)
#   Reel kur    : q_t  = q_{t-1} + Δe_t − π_t                             (artış = reel değer kaybı)
# Δe, π ve i aynı dönemde birbirini belirler; her dönem 3x3 eşanlı sistem kapalı biçimde çözülür.

DEGISKENLER = ["y", "pi", "i", "de", "q"]
ETIKET = {
    "y": "Çıktı açığı",
    "pi": "Enflasyon",
    "i": "Politika faizi",
    "de": "Nominal kur değişimi",
    "q": "Reel kur",
}
SOKLAR = {
    "kur": "Kur şoku (risk primi)",
    "faiz": "Para politikası şoku",
    "maliyet": "Maliyet şoku",
    "talep": "Talep şoku",
}

VARSAYILAN = dict(
    rho_y=0.60, sigma=0.15, delta=0.05,
    rho_pi=0.60, kappa=0.10, gamma=0.20,
    phi_pi=1.50, phi_y=0.50, rho_i=0.70,
    theta=0.50,
)


@dataclass
class SimSonuc:
    yol: dict[str, np.ndarray]
    max_kok: float          # geçiş matrisinin en büyük özdeğer modülü
    tekil: bool             # eşanlı sistem çözülemiyor mu


def _adim(s, p, e):
    """Bir dönem ilerlet. s = (y, pi, i, q) önceki dönem; e = şok vektörü."""
    y0, pi0, i0, q0 = s
    y = p["rho_y"] * y0 - p["sigma"] * (i0 - pi0) + p["delta"] * q0 + e["talep"]
    a_pi = p["rho_pi"] * pi0 + p["kappa"] * y0 + e["maliyet"]
    a_i = p["rho_i"] * i0 + (1 - p["rho_i"]) * p["phi_y"] * y + e["faiz"]
    b = (1 - p["rho_i"]) * p["phi_pi"]
    D = 1 + p["gamma"] * p["theta"] * (b - 1)
    pi = (a_pi - p["gamma"] * p["theta"] * a_i + p["gamma"] * e["kur"]) / D
    i = a_i + b * pi
    de = -p["theta"] * (i - pi) + e["kur"]
    q = q0 + de - pi
    return (y, pi, i, q), de, D


def gecis_matrisi(p) -> np.ndarray:
    """Model doğrusal olduğu için s_t = A s_{t-1}; A'yı birim vektörlerle elde ederiz."""
    sifir = {k: 0.0 for k in SOKLAR}
    A = np.zeros((4, 4))
    for j in range(4):
        s = np.zeros(4)
        s[j] = 1.0
        yeni, _, _ = _adim(tuple(s), p, sifir)
        A[:, j] = yeni
    return A


def simule_et(p: dict, sok: str, buyukluk: float, kalicilik: float, ufuk: int = 20) -> SimSonuc:
    b = (1 - p["rho_i"]) * p["phi_pi"]
    D = 1 + p["gamma"] * p["theta"] * (b - 1)
    tekil = abs(D) < 0.05
    yol = {k: np.zeros(ufuk + 1) for k in DEGISKENLER}
    if tekil:
        return SimSonuc(yol, np.inf, True)

    s = (0.0, 0.0, 0.0, 0.0)
    eps = buyukluk
    for t in range(ufuk + 1):
        e = {k: 0.0 for k in SOKLAR}
        e[sok] = eps
        s, de, _ = _adim(s, p, e)
        for k, v in zip(["y", "pi", "i", "q"], s):
            yol[k][t] = v
        yol["de"][t] = de
        eps *= kalicilik
    max_kok = float(np.max(np.abs(np.linalg.eigvals(gecis_matrisi(p)))))
    return SimSonuc(yol, max_kok, False)


# ---------------------------------------------------------------------------
# 2) VAR(p) + Cholesky + bootstrap
# ---------------------------------------------------------------------------
VAR_DEG = ["kur", "enf", "faiz"]
VAR_ETIKET = {
    "kur": "Kur değişimi (aylık %, Δlog USD/TRY)",
    "enf": "Enflasyon (aylık %, Δlog TÜFE)",
    "faiz": "Politika faizi (yıllık %)",
}


def siralamalar():
    return list(itertools.permutations(VAR_DEG))


def _tasarim(Y: np.ndarray, p: int, D: np.ndarray | None):
    """Y: T×k. Döner: X (T-p)×(1+kp+d), Yt (T-p)×k."""
    T, k = Y.shape
    satirlar = []
    for t in range(p, T):
        gec = np.concatenate([Y[t - l] for l in range(1, p + 1)])
        det = [1.0] + (list(D[t]) if D is not None else [])
        satirlar.append(np.concatenate([det, gec]))
    return np.asarray(satirlar), Y[p:]


def var_tahmin(Y, p, D=None):
    X, Yt = _tasarim(Y, p, D)
    B, *_ = np.linalg.lstsq(X, Yt, rcond=None)          # (m)×k
    U = Yt - X @ B
    n, m = X.shape
    Sigma = U.T @ U / (n - m)
    return B, U, Sigma, X


def katsayi_matrisleri(B, k, p, ndet):
    """B'den A_1..A_p (her biri k×k, satır = denklem)."""
    return [B[ndet + l * k: ndet + (l + 1) * k, :].T for l in range(p)]


def max_kok(A_list):
    k = A_list[0].shape[0]
    p = len(A_list)
    C = np.zeros((k * p, k * p))
    C[:k, :] = np.hstack(A_list)
    if p > 1:
        C[k:, :-k] = np.eye(k * (p - 1))
    return float(np.max(np.abs(np.linalg.eigvals(C))))


def irf(A_list, P, ufuk):
    """Ortogonal etki-tepki: Θ_h = Φ_h P. Döner: (ufuk+1)×k×k  [h, yanıt, şok]."""
    k = P.shape[0]
    p = len(A_list)
    Phi = [np.eye(k)]
    for h in range(1, ufuk + 1):
        M = np.zeros((k, k))
        for l in range(1, min(h, p) + 1):
            M += A_list[l - 1] @ Phi[h - l]
        Phi.append(M)
    return np.array([F @ P for F in Phi])


@dataclass
class VarSonuc:
    nokta: np.ndarray        # (H+1)×k×k   — orijinal değişken sırasında (VAR_DEG)
    alt68: np.ndarray
    ust68: np.ndarray
    alt90: np.ndarray
    ust90: np.ndarray
    gecis: dict | None       # kur şokunda birikimli geçişkenlik oranı
    max_kok: float
    gozlem: int
    reddedilen: int          # patlayan bootstrap çekilişi sayısı


def var_analiz(veri: np.ndarray, sira: tuple, p: int, ufuk: int,
               D: np.ndarray | None = None, B_sayi: int = 200,
               tohum: int = 2026) -> VarSonuc:
    """
    veri: T×3, sütunlar VAR_DEG sırasında.
    sira: Cholesky sıralaması (ör. ('kur','enf','faiz')): ilk değişken eşanlı olarak en dışsal.
    """
    idx = [VAR_DEG.index(v) for v in sira]
    geri = np.argsort(idx)
    Y = veri[:, idx]
    k = Y.shape[1]
    ndet = 1 + (D.shape[1] if D is not None else 0)

    B, U, Sigma, X = var_tahmin(Y, p, D)
    A = katsayi_matrisleri(B, k, p, ndet)
    P = np.linalg.cholesky(Sigma)
    nokta = irf(A, P, ufuk)
    kok = max_kok(A)

    # --- Bootstrap (kalıntı yeniden örnekleme, özyinelemeli tasarım) ---
    rng = np.random.default_rng(tohum)
    T = Y.shape[0]
    cekilis = []
    reddedilen = 0
    Ub = U - U.mean(axis=0)
    detB = B[:ndet, :]
    while len(cekilis) < B_sayi and reddedilen < 5 * B_sayi:
        secim = rng.integers(0, Ub.shape[0], size=T - p)
        Ys = np.zeros_like(Y)
        Ys[:p] = Y[:p]
        for t in range(p, T):
            det = np.concatenate([[1.0], D[t]]) if D is not None else np.array([1.0])
            v = det @ detB
            for l in range(1, p + 1):
                v = v + A[l - 1] @ Ys[t - l]
            Ys[t] = v + Ub[secim[t - p]]
        Bs, _, Ss, _ = var_tahmin(Ys, p, D)
        As = katsayi_matrisleri(Bs, k, p, ndet)
        if max_kok(As) >= 1.0:
            reddedilen += 1
            continue
        try:
            Ps = np.linalg.cholesky(Ss)
        except np.linalg.LinAlgError:
            reddedilen += 1
            continue
        cekilis.append(irf(As, Ps, ufuk))
    cekilis = np.array(cekilis) if cekilis else np.repeat(nokta[None], 2, axis=0)

    def _ger(a):  # sıralamayı orijinal değişken düzenine döndür (yanıt ve şok eksenleri)
        return a[..., geri, :][..., :, geri]

    nokta_o = _ger(nokta)
    cek_o = _ger(cekilis)
    q = lambda x: np.percentile(cek_o, x, axis=0)

    # Birikimli kur geçişkenliği: Σ Δp / Σ Δe, kur şokuna yanıt
    ik, ie = VAR_DEG.index("kur"), VAR_DEG.index("enf")
    def _oran(a):
        ce = np.cumsum(a[..., :, ik, ik], axis=-1)
        cp = np.cumsum(a[..., :, ie, ik], axis=-1)
        return cp / ce
    gecis = {
        "nokta": _oran(nokta_o),
        "alt68": np.percentile(_oran(cek_o), 16, axis=0),
        "ust68": np.percentile(_oran(cek_o), 84, axis=0),
    }

    return VarSonuc(nokta_o, q(16), q(84), q(5), q(95), gecis, kok,
                    X.shape[0], reddedilen)


def mevsim_kuklalari(aylar: np.ndarray) -> np.ndarray:
    """11 aylık kukla (Ocak referans)."""
    return np.column_stack([(aylar == m).astype(float) for m in range(2, 13)])
