"""
Ekonometrik Gösterge Simülatörü — Shiny for Python uygulaması.
Yerelde:   shiny run app/app.py
Tarayıcıda (sunucusuz): shinylive export app site
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
from shiny import App, reactive, render, ui

import model as m

# --------------------------------------------------------------------------- görünüm
RENK = {"y": "#3E7C5A", "pi": "#9E2A2B", "i": "#1F4E79", "de": "#B8860B", "q": "#6B5B95",
        "kur": "#B8860B", "enf": "#9E2A2B", "faiz": "#1F4E79"}
MUREKKEP = "#1C2733"
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10, "axes.edgecolor": "#9AA3AD", "axes.labelcolor": MUREKKEP,
    "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "axes.spines.top": False, "axes.spines.right": False,
    "xtick.color": "#5A6570", "ytick.color": "#5A6570",
    "axes.grid": True, "grid.color": "#E3E6EA", "grid.linewidth": 0.8,
})

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&display=swap');
body { font-family: 'IBM Plex Sans', system-ui, sans-serif; color: #1C2733; }
.navbar-brand { font-weight: 600; letter-spacing: -0.01em; }
.aciklama { max-width: 72ch; color: #3B4652; font-size: 0.95rem; }
.uyari { border-left: 3px solid #9E2A2B; padding: 0.4rem 0.8rem; background: #FBF3F3; max-width: 72ch; }
.olcu { font-variant-numeric: tabular-nums; color: #3B4652; font-size: 0.9rem; }
.bslider .irs-bar, .bslider .irs-single { background: #1F4E79; border-color: #1F4E79; }
"""

VERI_YOLU = Path(__file__).parent / "data" / "turkiye_aylik.csv"


def veri_yukle():
    if not VERI_YOLU.exists():
        return None
    df = pd.read_csv(VERI_YOLU)
    df["tarih"] = pd.to_datetime(df["tarih"], format="%Y-%m")
    df = df.sort_values("tarih").reset_index(drop=True)
    df["kur"] = 100 * np.log(df["usdtry"]).diff()
    df["enf"] = 100 * np.log(df["tufe"]).diff()
    # ardışık olmayan aylardaki farkları geçersiz say
    ardisik = df["tarih"].diff().dt.days.between(27, 32)
    df.loc[~ardisik, ["kur", "enf"]] = np.nan
    return df.dropna(subset=["kur", "enf", "faiz"]).reset_index(drop=True)


VERI = veri_yukle()
AD = {"kur": "Kur", "enf": "Enflasyon", "faiz": "Faiz"}


def kaydirici(id_, etiket, mn, mx, adim):
    return ui.input_slider(id_, etiket, min=mn, max=mx, value=m.VARSAYILAN[id_], step=adim)


# --------------------------------------------------------------------------- arayüz
teorik_panel = ui.layout_sidebar(
    ui.sidebar(
        ui.input_select("sok", "Şok", {k: v for k, v in m.SOKLAR.items()}),
        ui.input_slider("buyukluk", "Şok büyüklüğü", 0.1, 10.0, 1.0, step=0.1),
        ui.input_slider("kalicilik", "Şokun kalıcılığı (AR katsayısı)", 0.0, 0.95, 0.5, step=0.05),
        ui.accordion(
            ui.accordion_panel("Kur ve fiyatlar",
                kaydirici("gamma", "Kur geçişkenliği γ", 0.0, 0.8, 0.01),
                kaydirici("rho_pi", "Enflasyon ataleti ρπ", 0.0, 0.95, 0.05),
                kaydirici("kappa", "Phillips eğimi κ", 0.0, 0.5, 0.01),
                kaydirici("theta", "Faiz farkına kur duyarlılığı θ", 0.0, 2.0, 0.05)),
            ui.accordion_panel("Para politikası",
                kaydirici("phi_pi", "Enflasyona tepki φπ", 0.0, 3.0, 0.05),
                kaydirici("phi_y", "Çıktı açığına tepki φy", 0.0, 2.0, 0.05),
                kaydirici("rho_i", "Faiz yumuşatma ρi", 0.0, 0.95, 0.05)),
            ui.accordion_panel("Talep",
                kaydirici("rho_y", "Çıktı ataleti ρy", 0.0, 0.95, 0.05),
                kaydirici("sigma", "Reel faize duyarlılık σ", 0.0, 0.5, 0.01),
                kaydirici("delta", "Reel kura duyarlılık δ", 0.0, 0.3, 0.01)),
            open="Kur ve fiyatlar",
        ),
        ui.input_slider("ufuk_t", "Ufuk (dönem)", 8, 40, 20, step=1),
        ui.div(
            ui.input_action_button("sabitle", "Bu senaryoyu karşılaştırma için sabitle", class_="btn-sm btn-outline-primary w-100"),
            ui.input_action_button("temizle", "Karşılaştırmayı kaldır", class_="btn-sm btn-link w-100"),
            ui.input_action_button("sifirla", "Parametreleri varsayılana döndür", class_="btn-sm btn-link w-100"),
        ),
        width=330,
    ),
    ui.p("Parametreleri değiştirin; etki-tepki yolları anında yeniden hesaplanır. "
         "Kesikli çizgiler sabitlediğiniz senaryodur.", class_="aciklama"),
    ui.output_plot("teorik_grafik", height="560px"),
    ui.output_ui("teorik_durum"),
)

if VERI is not None:
    ilk, son = VERI["tarih"].min().date(), VERI["tarih"].max().date()
    var_kenar = ui.sidebar(
        ui.input_slider("donem", "Örneklem", min=ilk, max=son,
                        value=(max(ilk, pd.Timestamp("2011-01-01").date()), son),
                        time_format="%Y-%m"),
        ui.input_select("sira", "Cholesky sıralaması (soldaki eşanlı olarak en dışsal)",
                        {"|".join(s): " → ".join(AD[n] for n in s) for s in m.siralamalar()},
                        selected="kur|enf|faiz"),
        ui.input_select("var_sok", "Şok veren değişken",
                        AD),
        ui.input_slider("gecikme", "Gecikme sayısı p", 1, 6, 2),
        ui.input_checkbox("mevsim", "Aylık mevsim kuklaları ekle", True),
        ui.input_radio_buttons("bant", "Güven bandı", {"68": "%68", "90": "%90"}, selected="68", inline=True),
        ui.input_select("bsayi", "Bootstrap çekilişi", {"100": "100 (hızlı)", "200": "200", "500": "500 (yavaş)"}, selected="100"),
        ui.input_slider("ufuk_v", "Ufuk (ay)", 6, 36, 24),
        width=330,
    )
    var_panel = ui.layout_sidebar(
        var_kenar,
        ui.p("İndirgenmiş VAR, Cholesky tanımlaması. Sıralamayı ya da örneklemi değiştirip "
             "sonucun ne kadar oynadığını izleyin: bu duyarlılık, sonucun kendisi kadar bilgilendiricidir.",
             class_="aciklama"),
        ui.output_plot("var_grafik", height="620px"),
        ui.output_ui("var_durum"),
    )
else:
    var_panel = ui.div(
        ui.h4("Türkiye verisi henüz eklenmedi"),
        ui.markdown(
            "Bu sekme `app/data/turkiye_aylik.csv` dosyasını okur. Oluşturmak için:\n\n"
            "1. evds3.tcmb.gov.tr üzerinden ücretsiz API anahtarı alın.\n"
            "2. `EVDS_API_KEY=... python scripts/veri_cek.py` komutunu çalıştırın, "
            "ya da anahtarı GitHub deposuna `EVDS_API_KEY` sırrı olarak ekleyin; "
            "iş akışı veriyi her ay kendiliğinden günceller."),
        class_="aciklama p-4",
    )

yontem = ui.div(ui.markdown((Path(__file__).parent / "yontem.md").read_text(encoding="utf-8")),
                class_="aciklama p-4")

app_ui = ui.page_navbar(
    ui.nav_panel("Teorik model", teorik_panel),
    ui.nav_panel("Türkiye verisi (VAR)", var_panel),
    ui.nav_panel("Yöntem ve uyarılar", yontem),
    title="Ekonometrik Gösterge Simülatörü",
    header=ui.tags.style(CSS),
    fillable=False,
)


# --------------------------------------------------------------------------- sunucu
def server(input, output, session):
    sabit = reactive.value(None)

    @reactive.calc
    def parametreler():
        return {k: input[k]() for k in m.VARSAYILAN}

    @reactive.calc
    def teorik():
        return m.simule_et(parametreler(), input.sok(), input.buyukluk(),
                           input.kalicilik(), input.ufuk_t())

    @reactive.effect
    @reactive.event(input.sabitle)
    def _():
        sabit.set(teorik())

    @reactive.effect
    @reactive.event(input.temizle)
    def _():
        sabit.set(None)

    @reactive.effect
    @reactive.event(input.sifirla)
    def _():
        for k, v in m.VARSAYILAN.items():
            ui.update_slider(k, value=v)

    @render.plot
    def teorik_grafik():
        r = teorik()
        fig, eks = plt.subplots(3, 2, figsize=(9, 7.5))
        sirali = ["pi", "i", "de", "q", "y"]
        for ax, k in zip(eks.flat, sirali):
            t = np.arange(len(r.yol[k]))
            ax.axhline(0, color="#9AA3AD", lw=0.8)
            if sabit() is not None and len(sabit().yol[k]) == len(t):
                ax.plot(t, sabit().yol[k], color=RENK[k], lw=1.4, ls="--", alpha=0.55)
            ax.plot(t, r.yol[k], color=RENK[k], lw=2.2)
            ax.set_title(m.ETIKET[k])
        ax = eks.flat[5]
        ax.axis("off")
        ax.text(0, 0.85, m.SOKLAR[input.sok()], fontsize=11, weight="semibold", color=MUREKKEP)
        p = parametreler()
        ax.text(0, 0.62, f"γ = {p['gamma']:.2f}   φπ = {p['phi_pi']:.2f}   ρi = {p['rho_i']:.2f}",
                fontsize=10, color="#3B4652")
        ax.text(0, 0.45, f"En büyük kök = {r.max_kok:.3f}", fontsize=10,
                color="#9E2A2B" if r.max_kok >= 1 else "#3B4652")
        for a in eks.flat[3:5]:
            a.set_xlabel("dönem")
        for a in eks.flat[:5]:
            a.xaxis.set_major_locator(MaxNLocator(integer=True))
        fig.tight_layout()
        return fig

    @render.ui
    def teorik_durum():
        r = teorik()
        if r.tekil:
            return ui.div("Bu parametre birleşiminde kur, enflasyon ve faiz denklemleri eşanlı olarak "
                          "çözülemiyor (γ·θ·((1−ρi)φπ − 1) ≈ −1). Parametrelerden birini değiştirin.",
                          class_="uyari")
        if r.max_kok >= 1:
            return ui.div(f"Model kararsız (en büyük kök {r.max_kok:.3f} ≥ 1): şokun etkisi sönmüyor, "
                          "patlıyor. Faiz tepkisini (φπ) ya da kur duyarlılığını (θ) değiştirmeyi deneyin.",
                          class_="uyari")
        if r.max_kok > 0.97:
            return ui.div(f"En büyük kök {r.max_kok:.3f}: model durağan ama şoklar çok yavaş sönüyor. "
                          "Ufku uzatarak yolun tamamını görebilirsiniz.", class_="olcu")
        return None

    # ---------------- VAR
    if VERI is None:
        return

    @reactive.calc
    def var_sonuc():
        bas, bit = input.donem()
        d = VERI[(VERI["tarih"] >= pd.Timestamp(bas)) & (VERI["tarih"] <= pd.Timestamp(bit))]
        p = input.gecikme()
        if len(d) < 12 * p + 24:
            return None, len(d)
        Y = d[m.VAR_DEG].to_numpy()
        D = m.mevsim_kuklalari(d["tarih"].dt.month.to_numpy()) if input.mevsim() else None
        with ui.Progress() as pr:
            pr.set(message="Bootstrap güven bantları hesaplanıyor")
            sonuc = m.var_analiz(Y, tuple(input.sira().split("|")), p, input.ufuk_v(),
                                 D=D, B_sayi=int(input.bsayi()))
        return sonuc, len(d)

    @render.plot
    def var_grafik():
        r, n = var_sonuc()
        if r is None:
            return None
        js = m.VAR_DEG.index(input.var_sok())
        alt, ust = (r.alt68, r.ust68) if input.bant() == "68" else (r.alt90, r.ust90)
        kur_soku = input.var_sok() == "kur"
        fig, eks = plt.subplots(2, 2, figsize=(9, 7.5))
        H = np.arange(r.nokta.shape[0])
        for ax, v in zip(eks.flat, m.VAR_DEG):
            iv = m.VAR_DEG.index(v)
            ax.axhline(0, color="#9AA3AD", lw=0.8)
            ax.fill_between(H, alt[:, iv, js], ust[:, iv, js], color=RENK[v], alpha=0.16, lw=0)
            ax.plot(H, r.nokta[:, iv, js], color=RENK[v], lw=2.2)
            ax.set_title(m.VAR_ETIKET[v])
        ax = eks.flat[3]
        if kur_soku:
            g = r.gecis
            ax.axhline(0, color="#9AA3AD", lw=0.8)
            ax.fill_between(H, g["alt68"], g["ust68"], color="#9E2A2B", alpha=0.16, lw=0)
            ax.plot(H, g["nokta"], color="#9E2A2B", lw=2.2)
            ax.set_title("Birikimli kur geçişkenliği  ΣΔp / ΣΔe")
            ax.set_ylim(min(-0.2, np.nanmin(g["alt68"]) - 0.05), max(1.2, np.nanmax(g["ust68"]) + 0.05))
        else:
            ax.axis("off")
            ax.text(0, 0.7, "Geçişkenlik oranı yalnızca\nkur şokunda tanımlıdır.",
                    fontsize=10, color="#3B4652")
        for a in eks[1]:
            a.set_xlabel("ay")
        fig.suptitle(f"{AD[input.var_sok()]} değişkenine "
                     f"bir standart sapmalık şok", x=0.01, ha="left", fontsize=12, weight="semibold")
        for a in eks.flat:
            a.xaxis.set_major_locator(MaxNLocator(integer=True))
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        return fig

    @render.ui
    def var_durum():
        r, n = var_sonuc()
        if r is None:
            return ui.div(f"Seçilen örneklemde {n} gözlem var; {input.gecikme()} gecikmeli bir VAR için "
                          "örneklemi genişletin ya da gecikme sayısını azaltın.", class_="uyari")
        satirlar = [f"Kullanılan gözlem: {r.gozlem}", f"En büyük kök: {r.max_kok:.3f}"]
        if r.reddedilen:
            satirlar.append(f"Patlayan {r.reddedilen} bootstrap çekilişi atıldı.")
        if input.var_sok() == "kur":
            h = min(12, len(r.gecis["nokta"]) - 1)
            satirlar.append(f"12. ayda birikimli geçişkenlik: {r.gecis['nokta'][h]:.2f} "
                            f"(%68 aralık {r.gecis['alt68'][h]:.2f} – {r.gecis['ust68'][h]:.2f})")
        uyarilar = []
        if r.max_kok > 0.98:
            uyarilar.append(ui.div("En büyük kök 1'e çok yakın: sistem neredeyse birim köklü. "
                                   "Bantlar güvenilmez olabilir; örneklemi daraltmayı deneyin.", class_="uyari"))
        return ui.div(*[ui.div(s, class_="olcu") for s in satirlar], *uyarilar)


app = App(app_ui, server)
