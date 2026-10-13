@echo off
chcp 65001 >nul
title AegisData 公网启动器

echo ════════════════════════════════════════════════════
echo   AegisData 企业数据安全系统 — 公网启动器
echo ════════════════════════════════════════════════════
echo.
echo [1/3] 启动后端服务...
start "AegisData-Server" /min python app.py
timeout /t 3 /nobreak >nul

echo [2/3] 启动公网隧道...
echo.
echo    正在连接 localhost.run，请稍等...
echo    连接成功后会显示一个公网地址，把它发给别人就能访问
echo.
echo    注意：这个窗口不能关，关了公网就断了
echo ─────────────────────────────────────────────────────
echo.

ssh -o StrictHostKeyChecking=no -R 80:localhost:5000 nokey@localhost.run

echo.
echo 隧道已断开，按任意键退出...
pause >nul
