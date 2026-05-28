@echo off
cd /d D:\PROJETOS\loan_system

call venv\Scripts\activate

echo Iniciando Sistema de Emprestimos...
echo Acesse na rede: http://172.18.231.244:5000

waitress-serve --host=0.0.0.0 --port=5000 wsgi:app

pause