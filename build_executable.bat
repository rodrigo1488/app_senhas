@echo off
REM Script para gerar executável do App Senhas usando PyInstaller
REM Execute este arquivo no Windows

echo ========================================
echo   Gerando Executavel - App Senhas
echo ========================================
echo.

REM Verificar se PyInstaller está instalado
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo [ERRO] PyInstaller nao esta instalado!
    echo.
    echo Instalando PyInstaller...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERRO] Falha ao instalar PyInstaller!
        pause
        exit /b 1
    )
)

echo [OK] PyInstaller encontrado
echo.

REM Limpar builds anteriores
echo Limpando builds anteriores...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist AppSenhas.spec del /q AppSenhas.spec
echo [OK] Limpeza concluida
echo.

REM Testar imports primeiro
echo Testando imports...
python test_imports.py
if errorlevel 1 (
    echo.
    echo [ERRO] Alguns modulos estao faltando!
    echo Execute: pip install -r requirements.txt
    pause
    exit /b 1
)

REM Gerar executável
echo.
echo Gerando executavel...
echo.
echo Opcoes disponiveis:
echo 1. build_executable.spec (versao padrao)
echo 2. build_executable_v2.spec (versao robusta - recomendada)
echo.
set /p escolha="Escolha (1 ou 2, padrao=2): "
if "%escolha%"=="" set escolha=2
if "%escolha%"=="1" (
    echo Usando versao padrao...
    pyinstaller --clean build_executable.spec
) else (
    echo Usando versao robusta...
    pyinstaller --clean build_executable_v2.spec
)

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao gerar executavel!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Executavel gerado com sucesso!
echo ========================================
echo.
echo O executavel esta em: dist\AppSenhas.exe
echo.
echo IMPORTANTE:
echo - Copie a pasta 'dist' completa para onde desejar
echo - O executavel precisa dos arquivos da pasta 'dist'
echo - Na primeira execucao, crie o arquivo .env com:
echo   SUPABASE_URL=sua_url
echo   SUPABASE_KEY=sua_chave
echo.
pause

