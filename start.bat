
@echo off
setlocal EnableDelayedExpansion

echo Starting Warehouse Project...

:: Установка переменных
set "PROJECT_DIR=C:\Users\Admin\Desktop\warehouse"
set "FRONTEND_DIR=%PROJECT_DIR%\frontend"
set "BACKEND_DIR=%PROJECT_DIR%\backend"
set "VENV_DIR=%BACKEND_DIR%\venv"
set "FRONTEND_PORT=5177"
set "BACKEND_PORT=8000"
set "BROWSER_URL=http://localhost:%FRONTEND_PORT%/login"

:: Проверка, что папки существуют
if not exist "%FRONTEND_DIR%" (
    echo ERROR: Frontend directory %FRONTEND_DIR% does not exist.
    pause
    exit /b 1
)
if not exist "%BACKEND_DIR%" (
    echo ERROR: Backend directory %BACKEND_DIR% does not exist.
    pause
    exit /b 1
)

:: Опционально: Коммит и пуш изменений в Git
set /p GIT_COMMIT="Do you want to commit and push changes to Git? (y/n): "
if /i "!GIT_COMMIT!"=="y" (
    echo Committing and pushing changes...
    cd /d "%PROJECT_DIR%"
    git add .
    set /p COMMIT_MSG="Enter commit message (default: Update project): "
    if "!COMMIT_MSG!"=="" set "COMMIT_MSG=Update project"
    git commit -m "!COMMIT_MSG!"
    git push origin main
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Git push failed. Continuing with project startup...
        pause
    )
)

:: Запуск бэкенда
echo Starting backend...
cd /d "%BACKEND_DIR%"
if not exist "%VENV_DIR%" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%"
)
call "%VENV_DIR%\Scripts\activate.bat"
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Установка зависимостей бэкенда
if exist "requirements.txt" (
    echo Installing backend dependencies...
    pip install -r requirements.txt
)

:: Применение миграций Django
echo Applying Django migrations...
python manage.py migrate

:: Запуск Django сервера
start "Backend" cmd /k python manage.py runserver 0.0.0.0:%BACKEND_PORT%

:: Запуск фронтенда
echo Starting frontend...
cd /d "%FRONTEND_DIR%"
if not exist "node_modules" (
    echo Installing frontend dependencies...
    npm install
)

:: Запуск Vite
start "Frontend" cmd /k npm run dev -- --port %FRONTEND_PORT%

:: Ожидание, пока фронтенд запустится
timeout /t 5

:: Открытие браузера
echo Opening browser at %BROWSER_URL%...
start "" "%BROWSER_URL%"

echo Warehouse project started successfully!
pause
exit /b 0
