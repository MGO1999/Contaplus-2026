# dbf_writer.py — ContaPlus DBF writer (uses schema.json)
from datetime import date, datetime
import json
from pathlib import Path
from typing import List, Dict, Optional

PTA_RATE = 166.386
SCHEMA_PATH = Path(__file__).with_name("schema.json")

with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
    _SC = json.load(f)
_FIELDS = _SC["fields"]
_RECORD_LEN = int(_SC["record_len"])
_HEADER_LEN = int(_SC["header_len"])

def load_schema(_ignored=None):
    return _FIELDS, _RECORD_LEN, _HEADER_LEN

def _to_pta(eur: Optional[float]) -> Optional[float]:
    if eur is None: return None
    return float(int(round(float(eur) * PTA_RATE)))

def _enc_char(s, L):
    s = "" if s is None else str(s)
    b = s.encode("cp1252","ignore")[:L]
    return b.ljust(L, b" ")
def _enc_date(d):
    if isinstance(d,(date,datetime)): return f"{d:%Y%m%d}".encode("ascii")
    if isinstance(d,str) and len(d)==8 and d.isdigit(): return d.encode("ascii")
    return b" "*8
def _enc_num(x, L, D):
    if x is None: return b" "*L
    try:
        s = f"{float(x):>{L}.{D}f}"
    except Exception:
        s = " "*L
    return s[-L:].encode("ascii")
def _enc_field(f, v):
    t,L,D = f["type"], f["length"], f["decimals"]
    if t in ("C","M"): return _enc_char(v,L)
    if t == "D": return _enc_date(v)
    if t == "L": return b"T" if v else b"F"
    return _enc_num(v,L,D)

def write_dbf(path: Path, fields, record_len, header_len, rows: List[Dict]):
    today = date.today()
    header = bytearray(32)
    header[0] = 0x03
    header[1] = (today.year - 1900) & 0xFF
    header[2] = today.month
    header[3] = today.day
    header[4:8] = (len(rows)).to_bytes(4, 'little')
    header[8:10] = (header_len).to_bytes(2, 'little')
    header[10:12] = (record_len).to_bytes(2, 'little')
    header[29] = 0x00

    with open(path, "wb") as f:
        f.write(header)
        for fld in fields:
            desc = bytearray(32)
            name = fld["name"].encode("ascii","ignore")[:11]
            desc[0:len(name)] = name
            desc[11] = ord(fld["type"][0])
            desc[16] = fld["length"]
            desc[17] = fld["decimals"]
            f.write(desc)
        f.write(b"\x0D")
        for row in rows:
            rec = bytearray(record_len); rec[0] = 0x20; off = 1
            for fld in fields:
                data = _enc_field(fld, row.get(fld["name"]))
                if len(data) != fld["length"]:
                    data = data[:fld["length"]].ljust(fld["length"], b" ")
                rec[off:off+fld["length"]] = data; off += fld["length"]
            f.write(rec)
        f.write(b"\x1A")

def build_asiento_rows(fields_meta, asien:int, fecha:str, documento:str, proveedor:str, legs:List[Dict]) -> List[Dict]:
    names = {f["name"] for f in fields_meta}
    def row_template():
        return {f["name"]: None for f in fields_meta}
    rows = []
    for leg in legs:
        r = row_template()
        r["ASIEN"] = asien
        r["FECHA"] = fecha
        r["SUBCTA"] = leg["subcta"]
        r["CONCEPTO"] = f"Fra.{documento} {proveedor}"
        r["DOCUMENTO"] = documento[:10]
        r["MONEDAUSO"] = "2"
        ed = round(leg.get("euro_debe") or 0.0, 2); eh = round(leg.get("euro_haber") or 0.0, 2)
        r["EURODEBE"] = ed; r["EUROHABER"] = eh
        r["PTADEBE"] = _to_pta(ed); r["PTAHABER"] = _to_pta(eh)
        if "contra" in leg and leg["contra"] and "CONTRA" in names:
            r["CONTRA"] = leg["contra"]
        if "base" in leg and leg["base"] is not None:
            if "BASEEURO" in names: r["BASEEURO"] = round(leg["base"],2)
            if "BASEIMPO" in names: r["BASEIMPO"] = _to_pta(leg["base"])
        rows.append(r)
    # PTA balance on last line
    debe_pta = sum((r.get("PTADEBE") or 0.0) for r in rows)
    haber_pta = sum((r.get("PTAHABER") or 0.0) for r in rows)
    diff = int(round(debe_pta - haber_pta))
    if diff != 0:
        last = rows[-1]
        if diff > 0:
            last["PTAHABER"] = (last.get("PTAHABER") or 0.0) + float(abs(diff))
        else:
            last["PTADEBE"] = (last.get("PTADEBE") or 0.0) + float(abs(diff))
    # EUR sanity
    d_eur = sum((r.get("EURODEBE") or 0.0) for r in rows)
    h_eur = sum((r.get("EUROHABER") or 0.0) for r in rows)
    if round(d_eur - h_eur, 2) != 0.0:
        raise ValueError(f"Asiento {asien} not balanced in EUR: {d_eur} vs {h_eur}")
    return rows

def make_venta_asiento(fields_meta, asien:int, fecha:str, documento:str, proveedor:str, bases, rates, cuentas):
    if len(bases) != len(rates):
        raise ValueError("bases and rates must have equal length")
    bases = [round(float(b),2) for b in bases]
    rates = [round(float(r),2) for r in rates]
    ivas = [round(b * r / 100.0, 2) for b,r in zip(bases, rates)]
    total = round(sum(bases) + sum(ivas), 2)

    legs = []
    legs.append({"subcta": cuentas["CLIENTE"], "euro_debe": total})
    legs.append({"subcta": cuentas["BANCO"],  "euro_debe": total})
    for b, r in zip(bases, rates):
        legs.append({"subcta": cuentas["VENTAS"], "euro_haber": b})
        iva_sub = cuentas["IVA21"] if round(r,2)==21.00 else (cuentas["IVA10"] if round(r,2)==10.00 else cuentas["IVARED"])
        legs.append({"subcta": iva_sub, "euro_haber": round(b*r/100.0,2), "base": b, "contra": cuentas["CLIENTE"]})
    legs.append({"subcta": cuentas["CLIENTE"], "euro_haber": total})

    return build_asiento_rows(_FIELDS, asien, fecha, documento, proveedor, legs)
