# Architecture

PythOS Shell is a Python-based desktop shell/runtime environment. It runs on top of a host operating system and uses pygame to render a desktop-like interface.

The host operating system still provides kernel services, hardware access, filesystem access, process execution, and drivers. PythOS Shell provides the shell layer: windows, desktop icons, taskbar, start menu, app registry, and shell-managed app callbacks.

See the main `README.md` for the current Mermaid architecture diagram.

## Core Systems

| System | Responsibility |
|---|---|
| Shell Core | Starts the environment, stores global state, and coordinates subsystems. |
| Render System | Draws wallpaper, windows, taskbar, menus, dialogs, app content, and fitted/wrapped UI text. |
| Event Router | Reads pygame events and routes input to login, shell UI, windows, or app callbacks. |
| Window Manager | Creates, focuses, drags, snaps, minimizes, maximizes, and closes shell windows. |
| Desktop Manager | Handles desktop icons, wallpaper, and desktop launch behavior. |
| App Registry | Loads built-in and imported Python app manifests. |
| Runtime Data Manager | Handles config, user file root, cache, and installed-app folders. |
| Host Bridge | Polls host status such as network, battery, and USB mount information. |

## Current Boundary

PythOS Shell is not currently a full operating system. It is the shell/runtime layer. Future work may attach this shell layer to a Linux-kernel-based bootable system.
