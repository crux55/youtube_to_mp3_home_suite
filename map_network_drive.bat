@echo off
REM Script to map network drive for Docker Compose

echo Mapping network drive \\Uber-vault\ubervault to Z: drive...

REM Map the network drive
net use Z: \\Uber-vault\ubervault /persistent:yes

if %errorlevel% equ 0 (
    echo Successfully mapped \\Uber-vault\ubervault to Z:
    echo You can now run: docker-compose up --build
) else (
    echo Failed to map network drive. You may need to provide credentials:
    echo net use Z: \\Uber-vault\ubervault /user:DOMAIN\username password
)

pause
