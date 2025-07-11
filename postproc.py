import re

def ekstrak_nutrisi(text):
    nutrisi = {}
    cleaned_text = text.lower().replace(",", ".")

    targets = {
        "Takaran Saji": [r"takaran saji", r"serving size"],
        "Energi": [r"energi(?:\s*total)?", r"calories?", r"energy"],
        "Lemak": [r"lemak(?:\s*total)?", r"fat(?:\s*total)?"],
        "Gula": [r"gula(?:\s*total)?", r"sugars?"],
        "Serat": [r"serat(?:\s*total)?", r"fib(?:er|re)"],
        "Garam": [r"garam(?:\s*total)?", r"salt", r"sodium"],
        "Protein": [r"protein"],
        "Karbohidrat": [r"karbohidrat(?:\s*total)?", r"carbohydrates?", r"carbs?"],
        "Kalsium": [r"kalsium", r"calcium"]
    }

    for label, patterns in targets.items():
        for pattern in patterns:
            match = re.search(rf"{pattern}[^0-9]*(\d+\.?\d*)\s*(g|mg|ml|kkal|kcal)", cleaned_text)
            if match:
                try:
                    val = float(match.group(1))
                    unit = match.group(2)
                    nutrisi[label] = f"{val} {unit}"
                    break
                except ValueError:
                    continue  # Skip kalau gagal convert ke float

    return nutrisi


def konversi_ke_100g(nutrisi_dict, takaran_saji):
    hasil = {}
    if takaran_saji == 0:
        return hasil

    for nutrien, val_unit in nutrisi_dict.items():
        try:
            angka, satuan = val_unit.split()
            angka = float(angka)

            satuan = satuan.lower()
            if satuan in ["g", "mg", "ml"]:
                if satuan == "mg":
                    angka /= 1000  # Ubah mg ke g
                per_100g = (angka / takaran_saji) * 100
                hasil[nutrien] = f"{round(per_100g, 2)} g"
            elif satuan == "%":
                hasil[nutrien] = f"{angka} %"
            elif satuan == "kkal":
                hasil[nutrien] = f"{angka} kkal"
        except Exception:
            continue

    return hasil


def cek_kesehatan_bpom(kategori, nutrisi_dict):
    batas_bpom = {
        "Minuman Siap Konsumsi": {
            "Gula": {"max": 6.0, "satuan": "g/100ml"}
        },
        "Pasta & Mi Instan": {
            "Lemak": {"max": 20.0, "satuan": "g/100g"},
            "Garam": {"max": 900.0, "satuan": "mg/100g"}
        },
        "Susu Bubuk Plain": {
            "Gula": {"max": 12.5, "satuan": "g/100g"},
            "Kalsium": {"min": 15.0, "satuan": "% AKG/100g"}
        },
        "Susu Bubuk Rasa": {
            "Gula": {"max": 30.0, "satuan": "g/100g"},
            "Kalsium": {"min": 15.0, "satuan": "% AKG/100g"}
        },
        "Keju": {
            "Lemak": {"max": 30.0, "satuan": "g/100g"},
            "Garam": {"max": 900.0, "satuan": "mg/100g"},
            "Kalsium": {"min": 15.0, "satuan": "% AKG/100g"}
        },
        "Yogurt Plain": {
            "Lemak": {"max": 3.0},
            "Gula": {"max": 5.0},
            "Kalsium": {"min": 15.0}
        },
        "Yogurt Rasa": {
            "Lemak": {"max": 3.0},
            "Gula": {"max": 10.0},
            "Kalsium": {"min": 15.0}
        },
        "Serbuk Minuman Sereal": {
            "Lemak": {"max": 9.0},
            "Gula": {"max": 25.0},
            "Serat": {"min": 3.0}
        },
        "Oatmeal": {
            "Gula": {"max": 10.0},
            "Garam": {"max": 120.0},
            "Serat": {"min": 3.0}
        },
        "Sereal Siap Santap (Flake/Keping)": {
            "Lemak": {"max": 4.0},
            "Gula": {"max": 20.0},
            "Serat": {"min": 3.0}
        },
        "Sereal Batang (Bar)": {
            "Lemak": {"max": 10.0},
            "Gula": {"max": 20.0},
            "Serat": {"min": 3.0}
        },
        "Granola": {
            "Lemak": {"max": 9.0},
            "Gula": {"max": 25.0},
            "Serat": {"min": 3.0}
        },
        "Biskuit dan Kukis": {
            "Lemak": {"max": 20.0},
            "Gula": {"max": 20.0},
            "Garam": {"max": 300.0},
            "Serat": {"min": 3.0}
        },
        "Roti dan Produk Roti": {
            "Lemak": {"max": 10.0},
            "Gula": {"max": 15.0},
            "Garam": {"max": 300.0}
        },
        "Kue (Kue Kering dan Lembut)": {
            "Lemak": {"max": 15.0},
            "Gula": {"max": 25.0}
        },
        "Puding Siap Santap": {
            "Lemak": {"max": 5.0},
            "Gula": {"max": 10.0}
        },
        "Sambal": {
            "Garam": {"max": 1200.0}
        },
        "Kecap Manis": {
            "Gula": {"max": 40.0},
            "Garam": {"max": 1200.0}
        },
        "Makanan Ringan Siap Santap": {
            "Lemak": {"max": 20.0},
            "Garam": {"max": 400.0}
        }
    }

    hasil = []

    if kategori not in batas_bpom:
        return [f"Kategori **{kategori}** tidak ada dalam referensi BPOM."]

    batas = batas_bpom[kategori]

    for nutrien, batasan in batas.items():
        if nutrien not in nutrisi_dict:
            hasil.append(f"ℹ️ Data untuk **{nutrien}** tidak tersedia.")
            continue

        try:
            val = float(nutrisi_dict[nutrien].split()[0])
            satuan = batasan.get("satuan", "g/100g")

            if "max" in batasan:
                limit = batasan["max"]
                selisih = val - limit
                persen = (selisih / limit) * 100
                if selisih > 0:
                    hasil.append(
                        f"⚠️ **{nutrien}** = {val} {satuan} melebihi batas {limit} ({round(persen, 1)}% lebih tinggi)"
                    )
                else:
                    hasil.append(
                        f"✅ **{nutrien}** = {val} {satuan} sesuai batas maksimal {limit}"
                    )

            elif "min" in batasan:
                limit = batasan["min"]
                selisih = val - limit
                persen = (selisih / limit) * 100
                if selisih < 0:
                    hasil.append(
                        f"⚠️ **{nutrien}** = {val} {satuan} kurang dari batas minimal {limit} ({abs(round(persen, 1))}% lebih rendah)"
                    )
                else:
                    hasil.append(
                        f"✅ **{nutrien}** = {val} {satuan} sesuai atau melebihi batas minimal {limit}"
                    )

        except Exception:
            hasil.append(f"Gagal memproses nilai untuk {nutrien}.")

    return hasil

def auto_tidy_for_extraction(text):
    lines = text.split("\n")
    structured_lines = []
    buffer = ""

    for line in lines:
        line = line.strip()
        if re.search(r"\d+\s*(g|mg|kkal|%)", line.lower()):
            if buffer:
                structured_lines.append(f"{buffer} {line}")
                buffer = ""
            else:
                structured_lines.append(line)
        else:
            if buffer:
                structured_lines.append(buffer)  # flush jika tidak ada nilai
            buffer = line

    if buffer:
        structured_lines.append(buffer)

    return "\n".join(structured_lines)