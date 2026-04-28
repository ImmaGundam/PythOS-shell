# Runtime Data and Hand-Off Notes

PythOS Shell creates local runtime data while it runs. Review these files before sharing the project.

| Data / Folder | Purpose | Hand-Off Guidance |
|---|---|---|
| `desktop_config.json` | Local shell settings, username, wallpaper path, password hash/salt, app visibility, imported apps. | Do not share your personal copy. Use `desktop_config.example.json` instead. |
| User folder, such as `james/` or `users/<name>/` | Local user file root for File Manager. | Remove before public release unless intentionally shipping sample files. |
| `sys/cache/` | Temporary shell/cache data. | Clear before hand-off. |
| `sys/installed_apps/` | Imported Python app modules. | Clear for a clean release unless shipping examples. |
| `__pycache__/` and `*.pyc` | Python bytecode cache. | Remove. Python regenerates these automatically. |
| Local wallpaper paths | Machine-specific config data. | Replace with a default asset path or remove. |
| Password hash and salt | Shell login data. | Do not share real personal login data. |

Recommended clean hand-off:

1. Include source files and built-in app modules.
2. Include `desktop_config.example.json`.
3. Remove `desktop_config.json`.
4. Remove personal user folders.
5. Clear `sys/cache/` and `sys/installed_apps/`.
6. Keep empty runtime folders with `.gitkeep` if needed.
