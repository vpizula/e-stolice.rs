# -*- coding: utf-8 -*-
"""Obrada fotografija za e-stolice.rs.

Alat seče, smanjuje i lagano doteruje prave fotografije. Ne crta nove
scene i ne izrezuje predmet maskom. Boja se diže malo, kao na razvijanju
filma, da more i drvo ostanu verodostojni.

Pokretanje (Windows, iz korena projekta):

    py -3 tools/obrada_slika.py --manifest tools/kadar.json
    py -3 tools/obrada_slika.py --pecat assets/images/pecat-izvor.jpg --izlaz assets/images/pecat.png
    py -3 tools/obrada_slika.py --ulaz slike/stolica.jpg --izlaz assets/images/hero/more.jpg --sirina 1600 --seckanje 0,0,1,0.94 --boja 1.12
    py -3 tools/obrada_slika.py --serija-360 putanja/do/serije --izlaz-folder assets/images/360 --sirina 1200

--seckanje je levo,gore,desno,dole u udelu kadra (0 do 1), posle EXIF rotacije.
--pokrivanje 1200x630 seče sredinu na tačan format (Open Graph).
--mekana-ivica blago zamuti samo spoljnih 8% kadra. Ne dira stolicu u sredini.
Serija 360 očekuje fotografije istog predmeta redom i piše 01.jpg, 02.jpg…
i assets/images/360/frames.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent.parent


def otvori(putanja: Path) -> Image.Image:
    slika = Image.open(putanja)
    slika.load()
    return ImageOps.exif_transpose(slika)


def seckanje(slika: Image.Image, udeo) -> Image.Image:
    if not udeo:
        return slika
    levo, gore, desno, dole = [float(v) for v in udeo]
    sirina, visina = slika.size
    kutija = (
        int(round(sirina * levo)),
        int(round(visina * gore)),
        int(round(sirina * desno)),
        int(round(visina * dole)),
    )
    if kutija[2] <= kutija[0] or kutija[3] <= kutija[1]:
        raise ValueError("seckanje je prazno: %s" % (kutija,))
    return slika.crop(kutija)


def smanji(slika: Image.Image, sirina: int, duga: int = 0) -> Image.Image:
    if duga and max(slika.size) > duga:
        skala = duga / float(max(slika.size))
        return slika.resize((max(1, int(round(slika.width * skala))), max(1, int(round(slika.height * skala)))), Image.LANCZOS)
    if sirina and slika.width > sirina:
        visina = max(1, int(round(slika.height * (sirina / float(slika.width)))))
        return slika.resize((sirina, visina), Image.LANCZOS)
    return slika


def pokrij(slika: Image.Image, sirina: int, visina: int, sidro: str) -> Image.Image:
    skala = max(sirina / float(slika.width), visina / float(slika.height))
    nova_s = max(1, int(round(slika.width * skala)))
    nova_v = max(1, int(round(slika.height * skala)))
    slika = slika.resize((nova_s, nova_v), Image.LANCZOS)
    if sidro == "levo":
        x = 0
    elif sidro == "desno":
        x = nova_s - sirina
    else:
        x = (nova_s - sirina) // 2
    y = (nova_v - visina) // 2
    return slika.crop((x, y, x + sirina, y + visina))


def doteraj(slika: Image.Image, boja: float, kontrast: float, ostrina: float) -> Image.Image:
    if boja and abs(boja - 1) > 0.001:
        slika = ImageEnhance.Color(slika).enhance(boja)
    if kontrast and abs(kontrast - 1) > 0.001:
        slika = ImageEnhance.Contrast(slika).enhance(kontrast)
    if ostrina and abs(ostrina - 1) > 0.001:
        slika = ImageEnhance.Sharpness(slika).enhance(ostrina)
    return slika


def mekana_ivica(slika: Image.Image) -> Image.Image:
    """Blagi blur samo spoljne ivice. Sredina kadra, gde je stolica, ostaje oštra."""
    rgb = slika.convert("RGB")
    mutno = rgb.filter(ImageFilter.GaussianBlur(radius=2.2))
    maska = Image.new("L", rgb.size, 0)
    crtez = maska.load()
    sirina, visina = rgb.size
    rub_x = max(8, int(sirina * 0.08))
    rub_y = max(8, int(visina * 0.08))
    for y in range(visina):
        for x in range(sirina):
            dx = 0 if rub_x <= x < sirina - rub_x else min(x, sirina - 1 - x) / float(rub_x)
            dy = 0 if rub_y <= y < visina - rub_y else min(y, visina - 1 - y) / float(rub_y)
            udaljenost = max(dx, dy)
            if udaljenost < 1:
                jacina = int(round((1 - udaljenost) * 180))
                if jacina > 0:
                    crtez[x, y] = jacina
    return Image.composite(mutno, rgb, maska)


def sacuvaj(slika: Image.Image, izlaz: Path, kvalitet: int) -> None:
    izlaz.parent.mkdir(parents=True, exist_ok=True)
    sufiks = izlaz.suffix.lower()
    if sufiks in (".jpg", ".jpeg"):
        slika.convert("RGB").save(izlaz, "JPEG", quality=kvalitet, optimize=True, progressive=True)
    elif sufiks == ".webp":
        slika.convert("RGB").save(izlaz, "WEBP", quality=kvalitet, method=6)
    elif sufiks == ".png":
        slika.save(izlaz, "PNG", optimize=True)
    else:
        raise ValueError("Nepoznat format: %s" % izlaz)
    print("%s  %sx%s  %s KB" % (izlaz.relative_to(ROOT), slika.width, slika.height, izlaz.stat().st_size // 1024))


def u_projektu(putanja: str) -> Path:
    kandidat = Path(putanja)
    if not kandidat.is_absolute():
        kandidat = ROOT / kandidat
    return kandidat


def obradi_kadar(stavka: dict) -> None:
    ulaz = u_projektu(stavka["ulaz"])
    izlaz = u_projektu(stavka["izlaz"])
    slika = otvori(ulaz)
    slika = seckanje(slika, stavka.get("seckanje"))
    if stavka.get("pokrivanje"):
        sirina, visina = [int(v) for v in stavka["pokrivanje"]]
        slika = pokrij(slika, sirina, visina, stavka.get("sidro", "sredina"))
    else:
        slika = smanji(slika, int(stavka.get("sirina") or 0), int(stavka.get("duga") or 0))
    slika = doteraj(
        slika,
        float(stavka.get("boja") or 1),
        float(stavka.get("kontrast") or 1),
        float(stavka.get("ostrina") or 1.04),
    )
    if stavka.get("mekana_ivica"):
        slika = mekana_ivica(slika)
    sacuvaj(slika, izlaz, int(stavka.get("kvalitet") or 80))
    slika.close()


def svetla_neutralna(r, g, b, luma_granica, hroma_granica) -> bool:
    hroma = max(r, g, b) - min(r, g, b)
    luma = (r + g + b) / 3.0
    return hroma < hroma_granica and luma > luma_granica


def pecat_u_png(ulaz: Path, izlaz: Path, velicina: int) -> None:
    """Bela i svetlo siva šah-pozadina, spojena sa ivicom, postaje providna."""
    slika = otvori(ulaz).convert("RGBA")
    sirina, visina = slika.size
    pikseli = slika.load()
    vidjeno = bytearray(sirina * visina)
    red = []

    def gurni(x, y):
        indeks = y * sirina + x
        if vidjeno[indeks]:
            return
        r, g, b, _a = pikseli[x, y]
        if not svetla_neutralna(r, g, b, 186, 18):
            return
        vidjeno[indeks] = 1
        red.append((x, y))

    for x in range(sirina):
        gurni(x, 0)
        gurni(x, visina - 1)
    for y in range(visina):
        gurni(0, y)
        gurni(sirina - 1, y)

    glava = 0
    while glava < len(red):
        x, y = red[glava]
        glava += 1
        r, g, b, _a = pikseli[x, y]
        pikseli[x, y] = (r, g, b, 0)
        if x > 0:
            gurni(x - 1, y)
        if x + 1 < sirina:
            gurni(x + 1, y)
        if y > 0:
            gurni(x, y - 1)
        if y + 1 < visina:
            gurni(x, y + 1)

    for y in range(visina):
        for x in range(sirina):
            r, g, b, a = pikseli[x, y]
            if a == 0 or not svetla_neutralna(r, g, b, 170, 24):
                continue
            if (
                (x > 0 and pikseli[x - 1, y][3] == 0)
                or (x + 1 < sirina and pikseli[x + 1, y][3] == 0)
                or (y > 0 and pikseli[x, y - 1][3] == 0)
                or (y + 1 < visina and pikseli[x, y + 1][3] == 0)
            ):
                luma = (r + g + b) / 3.0
                alfa = 0 if luma > 205 else int((205 - luma) * 8)
                pikseli[x, y] = (r, g, b, max(0, min(255, alfa)))

    bbox = slika.getbbox()
    if not bbox:
        raise RuntimeError("Pečat je ostao prazan posle izreza pozadine.")
    levo = max(0, bbox[0] - 8)
    gore = max(0, bbox[1] - 8)
    desno = min(sirina, bbox[2] + 8)
    dole = min(visina, bbox[3] + 8)
    slika = slika.crop((levo, gore, desno, dole))
    if velicina and max(slika.size) > velicina:
        slika.thumbnail((velicina, velicina), Image.LANCZOS)
    sacuvaj(slika, izlaz, 80)


def serija_360(folder: Path, izlaz_folder: Path, sirina: int, kvalitet: int) -> None:
    ekstenzije = {".jpg", ".jpeg", ".png", ".webp"}
    fajlovi = sorted(p for p in folder.iterdir() if p.suffix.lower() in ekstenzije and p.is_file())
    if not fajlovi:
        raise SystemExit("Nema fotografija u %s" % folder)
    izlaz_folder.mkdir(parents=True, exist_ok=True)
    for stari in izlaz_folder.glob("[0-9][0-9].jpg"):
        stari.unlink()
    imena = []
    for redni, fajl in enumerate(fajlovi, start=1):
        ime = "%02d.jpg" % redni
        obradi_kadar({
            "ulaz": str(fajl),
            "izlaz": str(izlaz_folder / ime),
            "sirina": sirina,
            "kvalitet": kvalitet,
            "boja": 1.06,
            "kontrast": 1.03,
        })
        imena.append("assets/images/360/%s" % ime)
    (izlaz_folder / "frames.json").write_text(json.dumps(imena, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("frames.json  %s kadrova" % len(imena))


def main(argv) -> int:
    parser = argparse.ArgumentParser(description="Obrada fotografija e-stolice.rs")
    parser.add_argument("--manifest", help="JSON lista kadrova")
    parser.add_argument("--ulaz")
    parser.add_argument("--izlaz")
    parser.add_argument("--sirina", type=int, default=1600)
    parser.add_argument("--visina", type=int, default=0)
    parser.add_argument("--kvalitet", type=int, default=80)
    parser.add_argument("--seckanje", help="levo,gore,desno,dole u udelu 0-1")
    parser.add_argument("--boja", type=float, default=1.0)
    parser.add_argument("--kontrast", type=float, default=1.0)
    parser.add_argument("--ostrina", type=float, default=1.04)
    parser.add_argument("--mekana-ivica", action="store_true")
    parser.add_argument("--sidro", default="sredina", choices=("sredina", "levo", "desno"))
    parser.add_argument("--pecat", help="Ulazni pečat (JPEG ili PNG)")
    parser.add_argument("--pecat-velicina", type=int, default=320)
    parser.add_argument("--serija-360", dest="serija_360", help="Folder fotografija istog predmeta, redom")
    parser.add_argument("--izlaz-folder")
    args = parser.parse_args(argv)

    if args.manifest:
        stavke = json.loads((ROOT / args.manifest).read_text(encoding="utf-8"))
        for stavka in stavke:
            obradi_kadar(stavka)
        return 0

    if args.pecat:
        if not args.izlaz:
            raise SystemExit("--pecat traži --izlaz")
        pecat_u_png(Path(args.pecat) if Path(args.pecat).is_absolute() else ROOT / args.pecat, ROOT / args.izlaz, args.pecat_velicina)
        return 0

    if args.serija_360:
        folder = Path(args.serija_360)
        if not folder.is_absolute():
            folder = ROOT / folder
        izlaz = Path(args.izlaz_folder or "assets/images/360")
        if not izlaz.is_absolute():
            izlaz = ROOT / izlaz
        serija_360(folder, izlaz, args.sirina, args.kvalitet)
        return 0

    if args.ulaz and args.izlaz:
        seck = [float(v) for v in args.seckanje.split(",")] if args.seckanje else None
        stavka = {
            "ulaz": args.ulaz,
            "izlaz": args.izlaz,
            "sirina": args.sirina,
            "kvalitet": args.kvalitet,
            "seckanje": seck,
            "boja": args.boja,
            "kontrast": args.kontrast,
            "ostrina": args.ostrina,
            "mekana_ivica": args.mekana_ivica,
            "sidro": args.sidro,
        }
        if args.visina:
            stavka["pokrivanje"] = [args.sirina, args.visina]
        obradi_kadar(stavka)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
