# pdf_to_csv.py — Amazon ES optimized extractor (moves processed PDFs to ./out)
import re, csv, shutil
from pathlib import Path

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

DATE_IN_FILENAME = re.compile(r'(\d{2})-(\d{2})-(\d{4})')
DOC_RE           = re.compile(r'Número del documento\s+([A-Z0-9]+)', re.IGNORECASE)
VEND_RE          = re.compile(r'Vendido por\s+(.+)', re.IGNORECASE)
IVA_LINE = re.compile(r'(?m)^\s*(10|21)\s*%\s*([0-9\.\,]+)\s*€\s*([0-9\.\,]+)\s*€')
SHIP_DATE_RE = re.compile(r'Fecha de (?:envío|pedido)\s+(\d{2})\s+([a-záéíóúñ]+)\s+(\d{4})', re.IGNORECASE)

MONTHS = {
    'enero':'01','febrero':'02','marzo':'03','abril':'04','mayo':'05','junio':'06',
    'julio':'07','agosto':'08','septiembre':'09','setiembre':'09',
    'octubre':'10','noviembre':'11','diciembre':'12'
}

def dec_es(s: str) -> float:
    s = s.strip().replace('.', '').replace(',', '.')
    return float(s)

def extract_text(path: Path) -> str:
    if PdfReader is None: return ""
    try:
        reader = PdfReader(str(path))
        return "\n".join([(pg.extract_text() or "") for pg in reader.pages])
    except Exception:
        return ""

def date_from_filename(stem: str) -> str|None:
    m = DATE_IN_FILENAME.search(stem)
    if not m: return None
    dd, mm, yyyy = m.groups()
    return f"{yyyy}{mm}{dd}"

def date_from_pdf(text: str) -> str|None:
    m = SHIP_DATE_RE.search(text)
    if not m: return None
    dd, mon, yyyy = m.groups()
    mm = MONTHS.get(mon.lower())
    if not mm: return None
    return f"{yyyy}{mm}{dd}"

def main():
    base_dir = Path(__file__).parent
    inbox   = base_dir / "inbox"
    outdir  = base_dir / "out"
    outdir.mkdir(exist_ok=True)
    out_csv = outdir / "pending_invoices.csv"

    default_supplier = input("Enter supplier name (default Amazon): ").strip() or "Amazon"

    rows = []
    for pdf in sorted(inbox.glob("*.pdf")):
        text = extract_text(pdf)

        mdoc = DOC_RE.search(text)
        if mdoc:
            documento = mdoc.group(1)
        else:
            alt = re.search(r'(ES[0-9A-Z]+)', pdf.stem.replace(" ", ""))
            documento = alt.group(1) if alt else ""

        fecha = (date_from_pdf(text) or date_from_filename(pdf.stem) or "")

        msup = VEND_RE.search(text)
        proveedor = msup.group(1).strip() if msup else default_supplier

        bases, rates = [], []
        for m in IVA_LINE.finditer(text):
            rate = int(m.group(1))
            base = round(dec_es(m.group(2)), 2)
            if base > 0:
                bases.append(base); rates.append(rate)

        bases_str = "|".join(f"{b:.2f}" for b in bases)
        rates_str = "|".join(str(r) for r in rates)

        rows.append([fecha, documento, proveedor, bases_str, rates_str, pdf.name])

        # MOVE processed PDF into out/
        try:
            shutil.move(str(pdf), str(outdir / pdf.name))
        except Exception:
            target = outdir / pdf.name
            i = 1
            while target.exists():
                target = outdir / f"{pdf.stem} ({i}){pdf.suffix}"
                i += 1
            shutil.move(str(pdf), str(target))

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fecha","documento","proveedor","bases","rates","filename"])
        w.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_csv}")
    print("Processed PDFs moved to ./out. Now run run_make_dbf.bat.")

if __name__ == "__main__":
    main()
