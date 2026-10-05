"""
TCMB EVDS'den aylık veri çeker ve app/data/turkiye_aylik.csv dosyasını yazar.

Kullanım:
    export EVDS_API_KEY=...        # evds3.tcmb.gov.tr → profil sayfası → "Copy API Key"
    python scripts/veri_cek.py

Notlar (Ekim 2026 itibarıyla):
  * Eski evds2.tcmb.gov.tr/service/evds/ uç noktası 2025 sonunda kapandı; yeni adres evds3.
  * Anahtar HTTP başlığında ('key') gönderilir; parametreler yola eklenir ('?' kullanılmaz).
  * TÜFE 2025=100 bazına geçti. Uzun seri için eski (2003=100) ve yeni endeksin
    aylık log değişimleri zincirlenir: eski seri mevcut olduğu sürece eski, sonra yeni.
  * Seri kodlarını kullanmadan önce EVDS arayüzünden doğrulayın; aşağıdaki SERILER
    sözlüğünü değiştirmek yeterlidir.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
BASLANGIC = "01-01-2006"

SERILER = {
    # kod                      : (sütun adı,      aylık toplama)
    "TP.DK.USD.A.YTL":           ("usdtry",       "avg"),   # USD/TRY döviz alış, günlük → aylık ortalama
    "TP.FG.J0":                  ("tufe_eski",    "avg"),   # TÜFE 2003=100
    "TP.TUKFIY2025.GENEL":       ("tufe_yeni",    "avg"),   # TÜFE 2025=100
    "TP.APIFON4":                ("faiz",         "avg"),   # TCMB ağırlıklı ort. fonlama maliyeti (%)
}
# Not: Politika faizi olarak 'ağırlıklı ortalama fonlama maliyeti' seçildi; 2011–2018 faiz
# koridoru döneminde etkin para politikası duruşunu bir haftalık repodan daha iyi yansıtır.

CIKTI = Path(__file__).resolve().parents[1] / "app" / "data" / "turkiye_aylik.csv"


def cek(kodlar: list[str], aggs: list[str], anahtar: str) -> pd.DataFrame:
    bitis = date.today().strftime("%d-%m-%Y")
    yol = (f"series={'-'.join(kodlar)}&startDate={BASLANGIC}&endDate={bitis}"
           f"&type=json&frequency=5&aggregationTypes={'-'.join(aggs)}")
    r = requests.get(BASE + yol, headers={"key": anahtar}, timeout=60)
    r.raise_for_status()
    if "json" not in r.headers.get("Content-Type", ""):
        raise RuntimeError("EVDS JSON yerine başka içerik döndürdü (anahtar ya da uç nokta hatalı olabilir).")
    items = r.json().get("items", [])
    df = pd.DataFrame(items)
    if df.empty:
        raise RuntimeError(f"Boş yanıt: {kodlar}")
    df["tarih"] = pd.to_datetime(df["Tarih"], format="%Y-%m")
    out = df[["tarih"]].copy()
    for kod in kodlar:
        sutun = kod.replace(".", "_")
        out[SERILER[kod][0]] = pd.to_numeric(df.get(sutun), errors="coerce")
    return out


def tufe_zincirle(df: pd.DataFrame) -> pd.Series:
    """Eski ve yeni bazlı TÜFE'nin aylık log değişimlerini birleştirip tek endeks üret."""
    d_eski = np.log(df["tufe_eski"]).diff()
    d_yeni = np.log(df["tufe_yeni"]).diff()
    d = d_eski.where(d_eski.notna(), d_yeni)
    d.iloc[0] = 0.0
    gecerli = d.notna()
    ilk, son = gecerli.idxmax(), gecerli[::-1].idxmax()
    bosluk = df.loc[ilk:son, "tarih"][~gecerli.loc[ilk:son]]
    if len(bosluk):
        raise RuntimeError("TÜFE zincirinde boşluk var (eski ve yeni seri örtüşmüyor): "
                           + ", ".join(bosluk.dt.strftime("%Y-%m")))
    return (100 * np.exp(d.cumsum())).where(gecerli)


def main():
    anahtar = os.environ.get("EVDS_API_KEY")
    if not anahtar:
        sys.exit("EVDS_API_KEY ortam değişkeni tanımlı değil.")
    parcalar = []
    for kod, (_, agg) in SERILER.items():          # her seri ayrı istenir; farklı veri gruplarında olabilir
        parcalar.append(cek([kod], [agg], anahtar))
    df = parcalar[0]
    for p in parcalar[1:]:
        df = df.merge(p, on="tarih", how="outer")
    df = df.sort_values("tarih").reset_index(drop=True)
    df["tufe"] = tufe_zincirle(df)
    son = df[["tarih", "usdtry", "tufe", "faiz"]].dropna()
    CIKTI.parent.mkdir(parents=True, exist_ok=True)
    son.assign(tarih=son["tarih"].dt.strftime("%Y-%m")).to_csv(CIKTI, index=False)
    print(f"{len(son)} gözlem yazıldı: {son['tarih'].min():%Y-%m} – {son['tarih'].max():%Y-%m} → {CIKTI}")


if __name__ == "__main__":
    main()
