@echo off
SETLOCAL ENABLEDELAYEDEXPANSION
echo Scanning .\inbox for Amazon PDFs and creating out\pending_invoices.csv ...
python --version || (echo Python not found. Install Python 3.x and add to PATH. & pause & exit /b 1)
pip -q show PyPDF2 >nul 2>&1 || (echo Installing requirements... & pip install -r "%~dp0requirements.txt")
python "%~dp0pdf_to_csv.py"
echo( 
echo If the window closed immediately earlier, it was due to Python/requirements not installed
echo or an error. This script now PAUSES so you can read any message above.
pause
