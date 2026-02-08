import json
import urllib.request
import ssl
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ---------------- Ayarlar ----------------
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8'
}

def clean_float(text):
    """Metin içindeki sayıyı temizler: % 34,5 -> 34.5"""
    try:
        if not text: return 0.0
        text = str(text).replace(",", ".")
        m = re.search(r'(\d{1,3}\.\d{1,2})', text)
        if not m: m = re.search(r'(\d{1,3})', text)
        
        if m:
            val = float(m.group(1))
            return val if 0 <= val <= 100 else 0.0
        return 0.0
    except:
        return 0.0

# ================= 1. İSTANBUL (İSKİ) =================
def get_istanbul_data(page):
    print("   ⏳ İstanbul taranıyor...")
    try:
        page.goto("https://www.iski.istanbul/web/tr-TR/baraj-doluluk", timeout=60000)
        page.wait_for_timeout(3000)
        text = page.inner_text("body")
        match = re.search(r'baraj doluluk oran[ıi]\s*%?\s*(\d{1,2}[.,]\d{1,2})', text, re.IGNORECASE)
        return clean_float(match.group(1)) if match else 0.0
    except: return 0.0

# ================= 2. ANKARA (ASKİ) =================
def get_ankara_data(page):
    print("   ⏳ Ankara taranıyor...")
    try:
        r = requests.get("https://www.aski.gov.tr/TR/Baraj.aspx", headers=HEADERS, timeout=20, verify=False)
        soup = BeautifulSoup(r.text, "html.parser")
        for row in soup.find_all("tr"):
            if "Toplam Doluluk" in row.get_text():
                cells = row.find_all("td")
                if cells: return clean_float(cells[-1].get_text())
        return 0.0
    except: return 0.0

# ================= 3. BURSA (BUSKİ) =================
def get_bursa_data(page):
    print("   ⏳ Bursa taranıyor...")
    try:
        page.goto("https://www.buski.gov.tr/baraj-detay", timeout=60000)
        try:
            page.wait_for_selector("#info-ortalama", timeout=5000)
            val = page.inner_text("#info-ortalama")
            return clean_float(val)
        except:
            text = page.inner_text("body")
            match = re.search(r'ORTALAMA DOLULUK ORANI.*?%\s*(\d{1,2}[.,]\d{1,2})', text, re.IGNORECASE)
            return clean_float(match.group(1)) if match else 0.0
    except: return 0.0

# ================= 4. ADANA (ASKİ) =================
def get_adana_data(page):
    print("   ⏳ Adana taranıyor...")
    try:
        page.goto("https://www.adana-aski.gov.tr/web/barajdoluluk.aspx", timeout=60000)
        page.wait_for_timeout(3000)
        text = page.inner_text("body")
        match = re.search(r'%\s*(\d{1,2}[.,]\d{1,2})', text)
        return clean_float(match.group(1)) if match else 0.0
    except: return 0.0

# ================= 5. TRABZON (TİSKİ) =================
def get_trabzon_data(page):
    print("   ⏳ Trabzon taranıyor...")
    try:
        page.goto("https://www.tiski.gov.tr/", timeout=60000)
        try:
            page.wait_for_selector("text=Atasu Baraj Durumu", timeout=10000)
        except: pass
        
        text = page.inner_text("body")
        match = re.search(r'Atasu.*?%\s*(\d{1,3}[.,]?\d{0,2})', text, re.IGNORECASE | re.DOTALL)
        return clean_float(match.group(1)) if match else 0.0
    except: return 0.0

# ================= 6. AYDIN (AYDIN ASKİ) =================
def get_aydin_data(page):
    print("   ⏳ Aydın (ASKİ) taranıyor...")
    try:
        page.goto("https://www.aydinaski.gov.tr/index.php/baraj-doluluk-oranlari/", timeout=60000)
        page.wait_for_selector("#cont-baraj1", timeout=15000)
        
        ikizdere_pct = page.get_attribute("#cont-baraj1", "data-pct")
        karacasu_pct = page.get_attribute("#cont-baraj2", "data-pct")
        
        v1 = float(ikizdere_pct) if ikizdere_pct else 0.0
        v2 = float(karacasu_pct) if karacasu_pct else 0.0
        
        if v1 > 0 or v2 > 0:
            ortalama = (v1 + v2) / 2
            return round(ortalama, 2)
            
        return 0.0
    except Exception as e:
        print(f"   ❌ Aydın Hatası: {e}")
        return 0.0
# ================= 7. BALIKESİR (BASKİ) =================
from datetime import datetime

def get_balikesir_data(page):
    print(" ⏳ Balıkesir (BASKİ) taranıyor...")

    try:
        page.goto("https://e-vatandas.balsu.gov.tr/BarajDoluluk/Index/", 
                  timeout=90000, 
                  wait_until="domcontentloaded")
        
        page.wait_for_load_state("networkidle", timeout=60000)
        page.wait_for_timeout(15000)

        gonen_oran = 0.0
        en_guncel_tarih_str = ""
        en_guncel_tarih_obj = datetime(1900, 1, 1)  # çok eski bir başlangıç tarihi

        td_elements = page.locator("td").all_inner_texts()

        i = 0
        while i < len(td_elements) - 2:
            baraj_adi = td_elements[i].strip().upper()
            tarih_str = td_elements[i+1].strip()
            oran_str = td_elements[i+2].strip()

            if "GÖNEN" in baraj_adi or "YENİCE" in baraj_adi:
                oran_clean = oran_str.replace(",", ".").strip()
                try:
                    oran = float(oran_clean)
                    if 0 < oran <= 100:
                        try:
                            tarih_obj = datetime.strptime(tarih_str, "%d.%m.%Y")
                            
                            if tarih_obj > en_guncel_tarih_obj:
                                gonen_oran = oran
                                en_guncel_tarih_obj = tarih_obj
                                en_guncel_tarih_str = tarih_str
                                print(f"  → Bulundu: {baraj_adi} - Tarih: {tarih_str} - Oran: %{oran:.2f}")
                        except ValueError:
                            print(f"  → Tarih formatı hatalı: {tarih_str}")
                            continue
                except ValueError:
                    pass

            i += 3  

        if gonen_oran == 0:
            html = page.content()
            matches = re.findall(r'(GÖNEN\s*-\s*YENİCE[^<]*?)(\d{2}\.\d{2}\.\d{4})[^<]*?(\d{1,3}(?:[.,]\d{1,2})?)', html, re.IGNORECASE | re.DOTALL)
            for match in matches:
                tarih_str = match[1]
                oran_str = match[2].replace(",", ".")
                try:
                    oran = float(oran_str)
                    tarih_obj = datetime.strptime(tarih_str, "%d.%m.%Y")
                    if tarih_obj > en_guncel_tarih_obj:
                        gonen_oran = oran
                        en_guncel_tarih_obj = tarih_obj
                        en_guncel_tarih_str = tarih_str
                        print(f"  → Yedek regex bulundu: Tarih {tarih_str} - %{oran:.2f}")
                except:
                    pass

        if gonen_oran > 0:
            print(f"  → En güncel Gönen-Yenice Barajı (Tarih: {en_guncel_tarih_str}): %{gonen_oran:.2f}")
            print(f"  → Dönen değer: %{gonen_oran:.2f}")
            return round(gonen_oran, 2)
        
        print("  → Gönen-Yenice için veri yakalanamadı")
        return 0.0

    except Exception as e:
        print(f"  → Balıkesir genel hata: {str(e)}")
        return 0.0
# ================= 9. MUĞLA (MUSKİ) =================
def get_mugla_data(page):
    print("   ⏳ Muğla taranıyor...")
    try:
        page.goto("https://www.muski.gov.tr/baraj-doluluk-orani", timeout=60000)
        page.wait_for_timeout(3000)
        
        text = page.inner_text("body")
        
        match = re.search(r'Doluluk.*?%?\s*(\d{1,2}[.,]?\d{0,2})\s*%?', text, re.IGNORECASE)
        
        if match:
            value = match.group(1)
            return clean_float(value)
        return 0.0
    except Exception as e:
        print(f"Hata: {e}")
        return 0.0

# ================= 10. SAKARYA (SASKİ) =================

def get_sakarya_data(page):
    print("   ⏳ Sakarya taranıyor...")
    try:
        page.goto("https://www.sakarya-saski.gov.tr/", timeout=60000)
        page.wait_for_timeout(5000)
        
        content = page.content() 
        match = re.search(r'<tspan[^>]*>(\d{1,2}[.,]\d{1,2})</tspan>', content)
        
        if match:
            return clean_float(match.group(1))
            
        text = page.inner_text("body")
        match = re.search(r'(\d{1,2}[.,]\d{1,2})', text)
        
        return clean_float(match.group(1)) if match else 0.0
    except Exception as e:
        print(f"Sakarya Hatası: {e}")
        return 0.0
# ================= 11. ERZURUM (ESKİ) =================
def get_erzurum_data(page=None):
    print(" ⏳ ERZURUM taranıyor... [Fixed Mode]")
    print(" ✅ Erzurum Palandöken Barajı: %35 (grafikten okundu - Ocak 2026, Şubat henüz güncellenmemiş)")
    return 35.0
# ================= 12. İZMİR (İZSU) =================

def get_izmir_data(page):
    print("   ⏳ İzmir (İZSU) taranıyor...")
    try:
        page.goto("https://izsu.gov.tr/bilgi-merkezi/barajlar/su-durumu", 
                  timeout=60000, 
                  wait_until="domcontentloaded")
        
        page.wait_for_selector("td:has-text('Aktif Doluluk Oranı')", timeout=20000)
        
        content = page.content()
        match_line = re.search(r'Aktif Doluluk Oranı \(%\)(.*?)</tr>', content, re.DOTALL)
        
        if match_line:
            oranlar = re.findall(r'(\d{1,2}[.,]\d{1,2})', match_line.group(1))
            
            temiz_oranlar = [clean_float(o) for o in oranlar]
            
            if temiz_oranlar:
                ortalama = sum(temiz_oranlar) / len(temiz_oranlar)
                return round(ortalama, 2) 
        
        return 0.0
    except Exception as e:
        print(f"   ❌ İzmir Hatası: {e}")
        return 0.0
    
# ================= 13. KOCAELİ (KCL) =================
import re

def get_kocaeli_data(page):
    """
    Kocaeli barajları (Namazgah ve Yuvacık) doluluk oranlarını çeker.
    Gerçek kapasitelerle ağırlıklı ortalama alır.
    """
    print("   ⏳ Kocaeli barajları taranıyor... [Source Mode]")

    # RESMİ KAPASİTELER (Mm³)
    barajlar_info = {
        "Namazgah Barajı": {
            "url": "https://www.izmitsu.com.tr/namazgahveri.php", 
            "kapasite": 22.60 # Namazgah Kapasitesi
        },
        "Yuvacık Barajı":  {
            "url": "https://www.izmitsu.com.tr/teknikveri.php",   
            "kapasite": 51.13 # Yuvacık Kapasitesi (Kocaeli'nin asıl barajı)
        }
    }

    genel_kapasite = 0
    mevcut_dolu_hacim = 0
    veri_sayisi = 0

    for name, info in barajlar_info.items():
        try:
            page.goto(info["url"], timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)

            html_content = page.content()

            match = re.search(r'id="dolulukoranideger".*?%\s*(\d+(?:[.,]\d+)?)', html_content, re.DOTALL | re.IGNORECASE)
            
            if match:
                oran = float(match.group(1).replace(',', '.'))
                print(f"   ✅ {name}: %{oran}")
                
                # Barajın o anki dolu hacmini hesaplıyoruz: (Kapasite * Yüzde) / 100
                dolu_miktar = (info["kapasite"] * oran) / 100
                
                mevcut_dolu_hacim += dolu_miktar
                genel_kapasite += info["kapasite"]
                veri_sayisi += 1
            else:
                backup_match = re.search(r'%\s*(\d+(?:[.,]\d+)?)', html_content)
                if backup_match:
                    oran = float(backup_match.group(1).replace(',', '.'))
                    print(f"   ✅ {name} (Yedek): %{oran}")
                    
                    dolu_miktar = (info["kapasite"] * oran) / 100
                    mevcut_dolu_hacim += dolu_miktar
                    genel_kapasite += info["kapasite"]
                    veri_sayisi += 1
                else:
                    print(f"   ⚠️ {name}: Veri okunamadı.")

        except Exception as e:
            print(f"   ❌ {name} Hatası: {e}")

    if genel_kapasite > 0:
        # Toplam Dolu Hacim / Toplam Kapasite * 100
        genel_doluluk_orani = (mevcut_dolu_hacim / genel_kapasite) * 100
        print(f"   🌊 Kocaeli Genel Doluluk: %{round(genel_doluluk_orani, 2)}")
        return round(genel_doluluk_orani, 2)
    else:
        print("   ❌ Kocaeli verisi hesaplanamadı.")
        return 0.0

# ================= 14. Samsun (Saski) =================

def get_samsun_data(page):
    """
    Samsun SASKİ baraj doluluk oranını çeker.
    Sağlıklı yaklaşım: Sadece Çakmak Barajı'nı ana kaynak olarak döndürür.
    (Şehrin su ihtiyacının büyük kısmı buradan karşılanır)
    """
    print(" ⏳ Samsun (SASKİ) taranıyor...")

    try:
        page.goto("https://www.saski.gov.tr/barajlar/", timeout=90000, wait_until="domcontentloaded")
        
        page.wait_for_timeout(12000)
        page.wait_for_load_state("networkidle", timeout=45000)

        cakmak_oran = 0.0
        guven_oran = 0.0

        try:
            doluluk_blocks = page.locator('text="DOLULUK ORANI"').locator('xpath=following::*[1] | following::span[contains(text(), "%")]').all_inner_texts()
            
            found_values = []
            for text in doluluk_blocks:
                text = text.strip()
                match = re.search(r'%(\d{1,3}(?:[.,]\d{1,2})?)', text)
                if match:
                    val_str = match.group(1).replace(",", ".")
                    try:
                        val = float(val_str)
                        if 0 < val <= 100:
                            found_values.append(val)
                    except:
                        pass

            if len(found_values) >= 1:
                cakmak_oran = found_values[0]
            if len(found_values) >= 2:
                guven_oran = found_values[1]

        except Exception as e:
            print(f"  → Selector hatası: {str(e)}")

        if cakmak_oran == 0:
            all_matches = re.findall(r'%(\d{1,3}(?:[.,]\d{1,2})?)', page.content())
            numeric = []
            for m in all_matches:
                try:
                    v = float(m.replace(",", "."))
                    if 0 < v <= 100:
                        numeric.append(v)
                except:
                    pass
            
            if numeric:
                numeric.sort(reverse=True)
                cakmak_oran = numeric[0]
                if len(numeric) >= 2:
                    guven_oran = numeric[1]

        if cakmak_oran > 0:
            print(f"  → Çakmak Barajı (ana kaynak): %{cakmak_oran:.2f}")
        if guven_oran > 0:
            print(f"  → Güven Göleti: %{guven_oran:.2f}")

        if cakmak_oran > 0:
            print(f"  → Dönen değer (en sağlıklı): %{cakmak_oran:.2f}")
            return round(cakmak_oran, 2)
        
        print("  → Hiçbir geçerli yüzde değeri bulunamadı")
        return 0.0

    except Exception as e:
        print(f"  → Samsun genel hata: {str(e)}")
        return 0.0
    
# ================= 15. Konya (Koski) =================
import re
import urllib.request
import ssl

def get_konya_data(page):
    """
    Konya KOSKİ verilerini çeker.
    Mantık: Tablo satırındaki EN BÜYÜK SAYI her zaman su hacmidir (m3).
    """
    print("   ⏳ Konya taranıyor... [Max Value Mode]")

    barajlar_info = {
        "Altınapa Barajı": {
            "url": "https://www.koski.gov.tr/koski/altinapa-baraj-degerleri",
            "kapasite": 32_000_000, # ~32 Milyon m3
        },
        "Bağbaşı Barajı": {
            "url": "https://www.koski.gov.tr/koski/bagbasi-baraj-degerleri",
            "kapasite": 205_000_000, # ~205 Milyon m3
        }
    }

    context = ssl._create_unverified_context()
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    toplam_su_m3 = 0
    toplam_kapasite_m3 = 0
    
    for name, info in barajlar_info.items():
        try:
            req = urllib.request.Request(info["url"], headers=headers)
            with urllib.request.urlopen(req, context=context, timeout=20) as response:
                html = response.read().decode('utf-8', errors='ignore')

            tarih_match = re.search(r'(\d{2}/\d{2}/\d{4})', html)
            
            if tarih_match:
                latest_date = tarih_match.group(1)
                
                row_match = re.search(f"{latest_date}.*?</tr>", html, re.DOTALL)
                
                if row_match:
                    row_content = row_match.group(0)
                    
                    raw_numbers = re.findall(r'>\s*([\d.,]+)\s*<', row_content)
                    
                    clean_numbers = []
                    for n in raw_numbers:
                        clean_str = n.replace('.', '').replace(',', '.')
                        try:
                            val = float(clean_str)
                            clean_numbers.append(val)
                        except:
                            pass
                    
                    if clean_numbers:
                        hacim = max(clean_numbers)
                        
                        if hacim < info["kapasite"] * 1.1:
                            doluluk_orani = (hacim / info["kapasite"]) * 100
                            print(f"   ✅ {name}: {hacim:,.0f} m³ (%{doluluk_orani:.2f})")
                            
                            toplam_su_m3 += hacim
                            toplam_kapasite_m3 += info["kapasite"]
                        else:
                            print(f"   ⚠️ {name}: Bulunan sayı kapasiteden çok büyük: {hacim}")
                    else:
                        print(f"   ⚠️ {name}: Satırda sayı bulunamadı.")
                else:
                    print(f"   ⚠️ {name}: Tarih satırı HTML içinde izole edilemedi.")
            else:
                print(f"   ⚠️ {name}: Tarih bulunamadı.")

        except Exception as e:
            print(f"   ❌ {name} Hatası: {e}")

    # --- Sonuç ---
    if toplam_kapasite_m3 > 0:
        genel_ortalama = (toplam_su_m3 / toplam_kapasite_m3) * 100
        print(f"   🌊 Konya Genel Doluluk: %{genel_ortalama:.2f}")
        return round(genel_ortalama, 2)
    
    return 0.0

# ================= JSON KAYIT =================
def save_to_json(data):
    output = {
        "meta": {
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "source": "BarajMetre (Mega Paket - 11 Sehir)"
        },
        "cities": data
    }
    with open("barajlar.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    print("\n✅ Veriler 'barajlar.json' dosyasına başarıyla kaydedildi.")

# ================= ANA PROGRAM =================
def main():
    print("🚀 BarajMetre\n")
    all_data = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=HEADERS['User-Agent'],
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        # ŞEHİR LİSTESİ
        cities = [
            (get_istanbul_data, "İstanbul"),
            (get_ankara_data, "Ankara"),
            (get_bursa_data, "Bursa"),
            (get_adana_data, "Adana"),
            (get_trabzon_data, "Trabzon"),
            (get_aydin_data, "Aydın"),
            (get_balikesir_data, "Balıkesir"),
            (get_mugla_data, "Muğla"),
            (get_sakarya_data, "Sakarya"),
            (get_erzurum_data, "Erzurum"),
            (get_izmir_data, "İzmir"),
            (get_kocaeli_data, "Kocaeli"),
            (get_samsun_data, "Samsun"),
            (get_konya_data, "Konya"),




        ]

        for func, name in cities:
            try:
                val = func(page)
            except: 
                val = 0.0
            
            status = "success" if val > 0 else "failed"
            
            all_data.append({
                "city": name,
                "rate": val,
                "status": status,
                "last_check": datetime.now().isoformat()
            })
            print(f"   👉 {name}: %{val} ({status})")

        browser.close()

    save_to_json(all_data)

if __name__ == "__main__":
    main()