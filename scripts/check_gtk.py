#!/usr/bin/env python3
"""Preflight check for GTK availability in the active Python environment."""

from __future__ import annotations

import os


def _print_fix_steps() -> None:
    print("Fix steps:")
    print("  1) Install system GTK packages:")
    print("     Ubuntu/Debian:")
    print("     sudo apt install -y python3-gi gir1.2-gtk-3.0")
    print("     Arch Linux:")
    print("     sudo pacman -Syu --needed python-gobject gtk3")
    print("  2) Recommended: recreate venv with system package visibility:")
    print("     rm -rf .venv")
    print("     python3 -m venv .venv --system-site-packages")
    print("     source .venv/bin/activate")
    print("     pip install -r requirements.txt")
    print("     python scripts/check_gtk.py")
    print("  3) If you must use isolated venv, install native build dependencies first:")
    print("     Ubuntu/Debian:")
    print("     sudo apt install -y build-essential pkg-config cmake gobject-introspection libgirepository-2.0-dev libcairo2-dev python3-dev")
    print("     Arch Linux:")
    print("     sudo pacman -Syu --needed base-devel pkgconf cmake gobject-introspection cairo python")
    print("  4) See README GTK Troubleshooting for last-resort symlink workaround.")


def _print_display_fix_steps() -> None:
    print("Display fix steps:")
    print("  1) Check required env vars in this same shell:")
    print('     echo "$DISPLAY" "$WAYLAND_DISPLAY" "$XDG_RUNTIME_DIR"')
    print("  2) If running on WSL2, restart WSLg from Windows PowerShell:")
    print("     wsl --shutdown")
    print("     # reopen your Ubuntu shell")
    print("  3) Re-run this probe from the same activated venv:")
    print("     python scripts/check_gtk.py")


def main() -> int:
    try:
        import gi  # type: ignore
    except Exception as exc:
        print("[FAIL] Could not import 'gi' (PyGObject).")
        print(f"Reason: {exc.__class__.__name__}: {exc}")
        _print_fix_steps()
        return 1

    try:
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        from gi.repository import Gdk, Gtk  # type: ignore
    except Exception as exc:
        print("[FAIL] Could not import GTK 3.0 bindings via gi.repository.")
        print(f"Reason: {exc.__class__.__name__}: {exc}")
        _print_fix_steps()
        return 1

    init_result = Gtk.init_check(None)
    gtk_ready = bool(init_result[0]) if isinstance(init_result, tuple) else bool(init_result)
    display = Gdk.Display.get_default()
    display_name = display.get_name() if display is not None else "None"

    if not gtk_ready or display is None:
        print("[FAIL] GTK imported but could not connect to a display server.")
        print(f"DISPLAY={os.environ.get('DISPLAY', '(unset)')}")
        print(f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '(unset)')}")
        print(f"XDG_RUNTIME_DIR={os.environ.get('XDG_RUNTIME_DIR', '(unset)')}")
        print(f"Gtk.init_check()={gtk_ready}, Gdk.Display.get_default()={display_name}")
        _print_display_fix_steps()
        return 1

    print("[OK] GTK preflight passed (import + display connection succeeded).")
    print(f"Display backend is reachable: {display_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
