@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
python --version || (echo Python not found. Install Python 3.x and add to PATH. & pause & exit /b 1)
pip -q show pandas >nul 2>&1 || (echo Installing requirements... & pip install -r "%~dp0requirements.txt")
set /p ASIENTO=Enter starting asiento number: 
SET OUTDIR=%~dp0out
IF NOT EXIST "%OUTDIR%" mkdir "%OUTDIR%"
python "%~dp0excel_to_dbf.py" --infile "%OUTDIR%\pending_invoices.csv" --outdir "%OUTDIR%" --asiento %ASIENTO% --dbf diario_batch.dbf --log batch_log.csv
echo( 
echo Done. DBF and log are in the out\ folder.
pause
