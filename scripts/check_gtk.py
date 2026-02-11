#!/usr/bin/env python3
"""Preflight check for GTK availability in the active Python environment."""

from __future__ import annotations

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
        from gi.repository import Gtk  # type: ignore  # noqa: F401
    except Exception as exc:
        print("[FAIL] Could not import GTK 3.0 bindings via gi.repository.")
        print(f"Reason: {exc.__class__.__name__}: {exc}")
        _print_fix_steps()
        return 1

    print("[OK] GTK preflight passed (gi + Gtk 3.0 import succeeded).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
