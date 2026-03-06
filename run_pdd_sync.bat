@echo off
cd /d C:\Users\parvr\Projects\InvoiceIQ
call %USERPROFILE%\.venvs\pdd\Scripts\activate.bat
pdd --force sync
pause
