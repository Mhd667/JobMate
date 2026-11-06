@echo off
REM JobMate - cree les comptes de demonstration et leurs profils (voir backend\seed\seed_demo_accounts.py)
cd /d "%~dp0backend"
if not exist seed\demo-users.csv (
  echo Placez le fichier supabase-demo-users.csv dans backend\seed\ sous le nom demo-users.csv, puis relancez.
  pause
  exit /b 1
)
py -m seed.seed_demo_accounts --csv seed\demo-users.csv
pause
