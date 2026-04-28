# Plugin API

PythOS Shell apps are Python modules that expose a `register()` function.

The shell imports the module, calls `register()`, and expects a manifest dictionary describing the app.

## Minimal Manifest

```python
def register():
    return {
        "id": "example_app",
        "name": "Example App",
        "title": "Example App",
        "window_size": (420, 300),
        "default_position": (120, 120),
        "draw": draw,
        "on_click": on_click,
        "on_key": on_key,
        "on_open": on_open,
        "show_on_desktop": True,
        "show_in_start_menu": True,
    }
```

## Common Callbacks

| Callback | Purpose |
|---|---|
| `draw(env, screen, content_rect, font, small_font, window)` | Draw app UI. |
| `on_click(env, pos, window, button)` | Handle mouse clicks. |
| `on_key(env, event, window)` | Handle keyboard events. |
| `on_open(env, window)` | Run setup logic when the app opens. |

## Trust Model

Imported apps are Python modules and can execute Python code. Only import trusted modules.
