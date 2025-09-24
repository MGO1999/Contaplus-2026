# excel_to_dbf.py — read CSV/TXT/XLSX and generate DBF (skips zero-total rows)
import argparse, csv
from pathlib import Path
import pandas as pd
from dbf_writer import load_schema, write_dbf, make_venta_asiento
import yaml

def load_accounts(cfg_path: Path):
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg["accounts"]

def parse_pipes(s):
    if pd.isna(s) or s=="": return []
    return [float(x.replace(",", ".")) for x in str(s).split("|")]

def read_table(infile: Path, sheet: str|None):
    if infile.suffix.lower() == ".xlsx":
        return pd.read_excel(infile, sheet_name=sheet)
    return pd.read_csv(infile)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--infile", required=True, help="CSV/TXT/XLSX with columns: fecha,documento,proveedor,bases,rates")
    ap.add_argument("--sheet", default=None, help="Excel sheet name (optional)")
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--asiento", type=int, required=True)
    ap.add_argument("--dbf", default="diario_batch.dbf")
    ap.add_argument("--log", default="batch_log.csv")
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()

    df = read_table(Path(args.infile), args.sheet)
    fields, record_len, header_len = load_schema(None)
    cuentas = load_accounts(Path(args.config))

    rows = []
    log_rows = []
    asien = args.asiento

    for _, r in df.iterrows():
        fecha = str(r["fecha"])
        documento = str(r["documento"])
        proveedor = str(r.get("proveedor", "Amazon"))
        bases = parse_pipes(r["bases"])
        rates = parse_pipes(r["rates"])
        total = round(sum(bases) + sum([b*r/100 for b, r in zip(bases, rates)]), 2)

        if total <= 0:
            log_rows.append([documento, "SKIP", "total<=0 (fill bases/rates)"])
            continue

        rows += make_venta_asiento(fields, asien, fecha, documento, proveedor, bases, rates, cuentas)
        log_rows.append([documento, "OK", f"total={total:.2f}"])
        asien += 1

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)
    if rows:
        write_dbf(outdir / args.dbf, fields, record_len, header_len, rows)

    with open(outdir / args.log, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["documento","status","message"]); w.writerows(log_rows)

    print(f"Built {len(rows)} lines; see {outdir / args.log}")

if __name__ == "__main__":
    main()
