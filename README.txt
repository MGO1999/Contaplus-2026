
Amazon PDFs → CSV → DBF (ContaPlus) — working build with PAUSE and auto-move
---------------------------------------------------------------------------
1) Install: double-click run_extract.bat (it auto-installs requirements if needed)
2) Put PDFs into ./inbox
3) Run:  run_extract.bat  (keeps window open; moves PDFs to ./out; writes out/pending_invoices.csv)
4) Run:  run_make_dbf.bat (prompts for asiento; writes out/diario_batch.dbf + out/batch_log.csv)
