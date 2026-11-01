# Selenium UI checks

Selenium 4.51.0 and a matching Microsoft Edge driver (155.0.4283.62) are configured for this workspace.

Run a headless smoke check:

```powershell
$py = 'C:\Users\rah_66160\AppData\Local\Programs\Python\Python312\python.exe'
& $py scripts\check_ui_selenium.py --url https://example.com
```

Each run stores a JSON report and screenshot under `infrastructure/reports/ui-checks/`.

For a page that needs an already authenticated browser session, start Edge with `--remote-debugging-port=9222`, then attach without closing that browser:

```powershell
& $py scripts\check_ui_selenium.py --attach 127.0.0.1:9222 --url https://app.example.com
```

The current Windows environment terminates isolated Chromium sessions while their GPU process is unavailable. The runner includes the standard GPU-disable flags; if it still happens, use `--attach` with a user-opened Edge session or repair the workstation GPU/remote-desktop graphics policy.
