#!/usr/bin/env python3
"""GTK prototype shell launcher."""

from __future__ import annotations

import faulthandler
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import TextIO

_FAULT_LOG_FILE: TextIO | None = None


def _configure_runtime_logging(log_dir: Path) -> Path:
    log_path = log_dir / "gtk_shell.log"
    stream_handler = logging.StreamHandler(sys.stderr)
    log_format = "%(asctime)s %(levelname)s %(name)s: %(message)s"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers = [
            logging.FileHandler(log_path, encoding="utf-8"),
            stream_handler,
        ]
    except Exception:
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[stream_handler],
            force=True,
        )
        logging.getLogger("gtk_shell.app").exception(
            "Failed to initialize file logging at %s; continuing with stderr only",
            log_path,
        )
        return log_path

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers,
        force=True,
    )
    return log_path


def _enable_fault_logging(log_dir: Path) -> None:
    global _FAULT_LOG_FILE
    fault_log_path = log_dir / "gtk_shell_fault.log"
    try:
        _FAULT_LOG_FILE = open(fault_log_path, "a", encoding="utf-8")
        faulthandler.enable(_FAULT_LOG_FILE, all_threads=True)
    except Exception:
        if _FAULT_LOG_FILE is not None and not _FAULT_LOG_FILE.closed:
            _FAULT_LOG_FILE.close()
        _FAULT_LOG_FILE = None
        try:
            faulthandler.enable(all_threads=True)
        except Exception:
            logging.getLogger("gtk_shell.app").exception(
                "Failed to enable faulthandler"
            )
        else:
            logging.getLogger("gtk_shell.app").exception(
                "Failed to write faulthandler output to %s; using stderr",
                fault_log_path,
            )


def _disable_fault_logging() -> None:
    global _FAULT_LOG_FILE
    if faulthandler.is_enabled():
        faulthandler.disable()
    if _FAULT_LOG_FILE is not None and not _FAULT_LOG_FILE.closed:
        _FAULT_LOG_FILE.close()
    _FAULT_LOG_FILE = None


def _install_exception_hook() -> None:
    def _log_hook(exc_type, exc_value, exc_traceback):
        logging.getLogger("gtk_shell.app").error(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _log_hook


def _check_display() -> None:
    """Fail fast with actionable guidance if no GUI display is available."""
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        return

    msg = (
        "No GUI display detected.\n"
        "WSL check: run `echo \"$DISPLAY\"` and expect `:0` or `:0.0`.\n"
        "If empty, enable WSLg or X11 forwarding before launching GTK apps."
    )
    raise RuntimeError(msg)


def _import_gtk() -> tuple[ModuleType, ModuleType]:
    try:
        import gi  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "PyGObject is not available. Install GTK3 Python bindings first."
        ) from exc

    try:
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, Gtk  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "GTK3 introspection modules are unavailable. "
            "Install gir1.2-gtk-3.0 and python3-gi."
        ) from exc

    return Gtk, Gdk


def _check_gtk_display_connection(Gtk: ModuleType, Gdk: ModuleType) -> None:
    """Fail early if GTK cannot connect to a usable display server."""
    init_result = Gtk.init_check(None)
    if isinstance(init_result, tuple):
        gtk_ready = bool(init_result[0])
    else:
        gtk_ready = bool(init_result)

    display = Gdk.Display.get_default()
    if gtk_ready and display is not None:
        return

    display_env = os.environ.get("DISPLAY", "(unset)")
    wayland_env = os.environ.get("WAYLAND_DISPLAY", "(unset)")
    raise RuntimeError(
        "GTK could not connect to a display server.\n"
        f"DISPLAY={display_env}, WAYLAND_DISPLAY={wayland_env}\n"
        "Verify WSLg/X11 forwarding is active and reachable from this shell."
    )


def _load_css(Gtk: ModuleType, Gdk: ModuleType, css_path: Path) -> None:
    if not css_path.exists():
        return

    provider = Gtk.CssProvider()
    try:
        provider.load_from_path(str(css_path))
    except Exception:
        logging.getLogger("gtk_shell.app").warning(
            "CSS load failed for %s; continuing without custom styles",
            css_path,
            exc_info=True,
        )
        return

    screen = Gdk.Screen.get_default()
    if screen is not None:
        Gtk.StyleContext.add_provider_for_screen(
            screen,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    glade_path = base_dir / "ui" / "app.glade"
    css_path = base_dir / "ui" / "dark.css"
    log_dir = base_dir / "logs"
    log_path = _configure_runtime_logging(log_dir)
    _enable_fault_logging(log_dir)
    _install_exception_hook()
    logger = logging.getLogger("gtk_shell.app")
    logger.info("Starting Garak LLM Security Tester")

    try:
        _check_display()
        Gtk, Gdk = _import_gtk()
        _check_gtk_display_connection(Gtk, Gdk)

        if not glade_path.exists():
            raise FileNotFoundError(f"Missing UI file: {glade_path}")

        builder = Gtk.Builder()
        builder.add_from_file(str(glade_path))

        from controller import PrototypeController

        controller = PrototypeController(builder)
        builder.connect_signals(controller)
        _load_css(Gtk, Gdk, css_path)

        window = builder.get_object("main_window")
        if window is None:
            raise RuntimeError("Glade file does not define object id 'main_window'.")

        window.show_all()
        Gtk.main()
        logger.info("GTK prototype exited cleanly")
        return 0
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as exc:
        logger.exception("GTK prototype startup/runtime failure")
        print(f"[gtk-shell] startup failed: {exc}", file=sys.stderr)
        print(f"[gtk-shell] see log: {log_path}", file=sys.stderr)
        return 1
    finally:
        _disable_fault_logging()


if __name__ == "__main__":
    raise SystemExit(main())
