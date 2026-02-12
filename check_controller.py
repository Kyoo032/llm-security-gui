"""Step 1 (Framework Setup) and Step 2 (Authentication) controllers."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable, List, Optional

_HF_TOKEN_PATTERN = re.compile(r"^hf_[a-zA-Z0-9]{8,498}$")

import gi  # type: ignore
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # type: ignore

from hf_cli import HFCLIStatus, check_hf_cli_auth

try:
    from huggingface_hub import get_token as hf_get_token
except (ImportError, ModuleNotFoundError):
    hf_get_token = None


class CheckController:
    """Manages Step 1 (Garak detection) and Step 2 (HF authentication)."""

    def __init__(
        self,
        builder: Gtk.Builder,
        on_step1_done: Callable[[bool], None],
        on_step2_done: Callable[[bool], None],
    ) -> None:
        self.builder = builder
        self.logger = logging.getLogger("garak_gui.check_controller")
        self._on_step1_done = on_step1_done
        self._on_step2_done = on_step2_done

        self._garak_version: Optional[str] = None
        self._garak_path: Optional[str] = None
        self._hf_username: Optional[str] = None
        self._hf_cli_command: Optional[str] = None
        self._hf_token: Optional[str] = None
        self._check_in_progress = False

        self._build_step1()
        self._build_step2()

    # ── Step 1: Framework Setup ─────────────────────────────────────

    def _build_step1(self) -> None:
        page = self.builder.get_object("step_1_page")
        if page is None:
            return

        title = Gtk.Label(label="Step 1: Framework Setup")
        title.get_style_context().add_class("step-title")
        title.set_xalign(0)
        page.pack_start(title, False, False, 0)

        section = Gtk.Label(label="Garak Framework")
        section.get_style_context().add_class("section-title")
        section.set_xalign(0)
        section.set_margin_top(16)
        page.pack_start(section, False, False, 0)

        # Status box
        self._garak_status_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        self._garak_status_box.get_style_context().add_class("status-box")
        self._garak_status_box.set_margin_top(8)

        self._garak_status_label = Gtk.Label(label="Checking...")
        self._garak_status_label.get_style_context().add_class("status-pending")
        self._garak_status_label.set_xalign(0)
        self._garak_status_box.pack_start(self._garak_status_label, False, False, 0)

        self._garak_detail_label = Gtk.Label(label="")
        self._garak_detail_label.get_style_context().add_class("label-muted")
        self._garak_detail_label.set_xalign(0)
        self._garak_detail_label.set_no_show_all(True)
        self._garak_detail_label.hide()
        self._garak_status_box.pack_start(
            self._garak_detail_label, False, False, 0
        )

        page.pack_start(self._garak_status_box, False, False, 0)

        # Instruction (hidden by default)
        self._garak_instruction = Gtk.Label()
        self._garak_instruction.get_style_context().add_class("status-instruction")
        self._garak_instruction.set_markup(
            'Install with <b>pip install garak</b>'
        )
        self._garak_instruction.set_xalign(0)
        self._garak_instruction.set_margin_top(12)
        self._garak_instruction.set_no_show_all(True)
        self._garak_instruction.hide()
        page.pack_start(self._garak_instruction, False, False, 0)

        # Retry button for step 1
        self._garak_retry_btn = Gtk.Button(label="Retry")
        self._garak_retry_btn.get_style_context().add_class("nav-button-back")
        self._garak_retry_btn.set_margin_top(12)
        self._garak_retry_btn.set_halign(Gtk.Align.START)
        self._garak_retry_btn.set_no_show_all(True)
        self._garak_retry_btn.hide()
        self._garak_retry_btn.connect("clicked", self._on_garak_retry)
        page.pack_start(self._garak_retry_btn, False, False, 0)

        # Nav buttons
        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav.set_margin_top(24)

        self._step1_next_btn = Gtk.Button(label="Next: Authentication \u2192")
        self._step1_next_btn.get_style_context().add_class("nav-button-next")
        self._step1_next_btn.set_sensitive(False)
        nav.pack_end(self._step1_next_btn, False, False, 0)

        page.pack_start(nav, False, False, 0)
        page.show_all()

    def run_garak_check(self) -> None:
        """Detect Garak installation in a background thread."""
        self._garak_status_label.set_text("Checking...")
        self._reset_style(self._garak_status_label, "status-pending")
        self._garak_detail_label.hide()
        self._garak_instruction.hide()
        self._garak_retry_btn.hide()

        def _detect() -> None:
            found, version, path = self._detect_garak()
            GLib.idle_add(self._update_garak_ui, found, version, path)

        threading.Thread(target=_detect, daemon=True).start()

    @staticmethod
    def _detect_garak() -> tuple:
        """Check if garak is installed. Returns (found, version, path)."""
        garak_path = shutil.which("garak")

        # Try: python -m garak --version
        for cmd in [["garak", "--version"], ["python", "-m", "garak", "--version"]]:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=15,
                    check=False,
                )
                output = (result.stdout or "").strip()
                if not output:
                    output = (result.stderr or "").strip()

                if result.returncode == 0 or "garak" in output.lower():
                    version = "unknown"
                    for line in output.splitlines():
                        line_lower = line.strip().lower()
                        if "version" in line_lower or "garak" in line_lower:
                            # Extract version-like patterns
                            for part in line.strip().split():
                                if any(c.isdigit() for c in part):
                                    version = part.strip("v").strip(",")
                                    break
                            if version != "unknown":
                                break
                    path = garak_path or cmd[0]
                    return (True, version, path)
            except (subprocess.TimeoutExpired, OSError):
                continue

        return (False, None, None)

    def _update_garak_ui(
        self, found: bool, version: Optional[str], path: Optional[str]
    ) -> None:
        if found:
            self._garak_version = version
            self._garak_path = path
            display_version = version or "detected"
            self._garak_status_label.set_text(
                f"Garak v{display_version} detected"
            )
            self._reset_style(self._garak_status_label, "status-ok")
            if path:
                self._garak_detail_label.set_text(f"Location: {path}")
                self._garak_detail_label.show()
            self._garak_instruction.hide()
            self._garak_retry_btn.hide()
            self._step1_next_btn.set_sensitive(True)
            self._on_step1_done(True)
        else:
            self._garak_status_label.set_text("Garak not found")
            self._reset_style(self._garak_status_label, "status-fail")
            self._garak_instruction.show()
            self._garak_retry_btn.show()
            self._step1_next_btn.set_sensitive(False)
            self._on_step1_done(False)
        return GLib.SOURCE_REMOVE

    def _on_garak_retry(self, _widget) -> None:
        self.run_garak_check()

    # ── Step 2: Authentication ──────────────────────────────────────

    def _build_step2(self) -> None:
        page = self.builder.get_object("step_2_page")
        if page is None:
            return

        title = Gtk.Label(label="Step 2: HuggingFace Authentication")
        title.get_style_context().add_class("step-title")
        title.set_xalign(0)
        page.pack_start(title, False, False, 0)

        section = Gtk.Label(label="CLI Status")
        section.get_style_context().add_class("section-title")
        section.set_xalign(0)
        section.set_margin_top(16)
        page.pack_start(section, False, False, 0)

        # Status box
        self._hf_status_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=4
        )
        self._hf_status_box.get_style_context().add_class("status-box")
        self._hf_status_box.set_margin_top(8)

        self._hf_status_label = Gtk.Label(label="Checking...")
        self._hf_status_label.get_style_context().add_class("status-pending")
        self._hf_status_label.set_xalign(0)
        self._hf_status_box.pack_start(self._hf_status_label, False, False, 0)

        page.pack_start(self._hf_status_box, False, False, 0)

        # Instruction
        self._hf_instruction = Gtk.Label()
        self._hf_instruction.get_style_context().add_class("status-instruction")
        self._hf_instruction.set_markup(
            'Run <b>hf auth login</b> in your terminal, then click Retry'
        )
        self._hf_instruction.set_xalign(0)
        self._hf_instruction.set_margin_top(12)
        self._hf_instruction.set_no_show_all(True)
        self._hf_instruction.hide()
        page.pack_start(self._hf_instruction, False, False, 0)

        # Retry button
        self._hf_retry_btn = Gtk.Button(label="Retry")
        self._hf_retry_btn.get_style_context().add_class("nav-button-back")
        self._hf_retry_btn.set_margin_top(12)
        self._hf_retry_btn.set_halign(Gtk.Align.START)
        self._hf_retry_btn.set_no_show_all(True)
        self._hf_retry_btn.hide()
        self._hf_retry_btn.connect("clicked", self._on_hf_retry)
        page.pack_start(self._hf_retry_btn, False, False, 0)

        # Nav buttons
        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav.set_margin_top(24)

        self._step2_back_btn = Gtk.Button(label="\u2190 Back")
        self._step2_back_btn.get_style_context().add_class("nav-button-back")
        nav.pack_start(self._step2_back_btn, False, False, 0)

        self._step2_next_btn = Gtk.Button(label="Next: Model Selection \u2192")
        self._step2_next_btn.get_style_context().add_class("nav-button-next")
        self._step2_next_btn.set_sensitive(False)
        nav.pack_end(self._step2_next_btn, False, False, 0)

        page.pack_start(nav, False, False, 0)
        page.show_all()

    def run_hf_check(self) -> None:
        """Check HF CLI auth and token in a background thread."""
        self._hf_status_label.set_text("Checking...")
        self._reset_style(self._hf_status_label, "status-pending")
        self._hf_instruction.hide()
        self._hf_retry_btn.hide()

        if self._check_in_progress:
            return
        self._check_in_progress = True

        def _check() -> None:
            try:
                cli_status = check_hf_cli_auth()
                if not cli_status.installed:
                    GLib.idle_add(
                        self._update_hf_ui,
                        False,
                        cli_status.detail,
                        'Install HF CLI: <b>pip install "huggingface_hub[cli]"</b>, '
                        "then run <b>hf auth login</b> and click Retry",
                    )
                    return

                if not cli_status.authenticated:
                    login_cmd = (
                        "huggingface-cli login"
                        if cli_status.command == "huggingface-cli"
                        else "hf auth login"
                    )
                    GLib.idle_add(
                        self._update_hf_ui,
                        False,
                        cli_status.detail,
                        f"Run <b>{login_cmd}</b> in your terminal, then click Retry",
                    )
                    return

                self._hf_cli_command = cli_status.command
                self._hf_username = cli_status.username

                token = self._detect_hf_token()
                if not token:
                    GLib.idle_add(
                        self._update_hf_ui,
                        False,
                        "CLI authenticated but no token found in env/cache",
                        "Token file not found. Try running <b>hf auth login</b> again",
                    )
                    return

                if not _HF_TOKEN_PATTERN.match(token):
                    GLib.idle_add(
                        self._update_hf_ui,
                        False,
                        "Token has invalid format",
                        "Token must start with 'hf_'. Try <b>hf auth login</b> again",
                    )
                    return

                self._hf_token = token
                from api_handler import HuggingFaceAPIHandler

                handler = HuggingFaceAPIHandler(token)
                ok, message = handler.validate_key()
                username = self._hf_username or "user"
                if ok:
                    GLib.idle_add(
                        self._update_hf_ui,
                        True,
                        f"Authenticated as {username}",
                        "",
                    )
                else:
                    GLib.idle_add(
                        self._update_hf_ui,
                        False,
                        message,
                        "Token validation failed. Try <b>hf auth login</b> again",
                    )
            finally:
                GLib.idle_add(self._clear_check_flag)

        threading.Thread(target=_check, daemon=True).start()

    @staticmethod
    def _detect_hf_token() -> Optional[str]:
        """Find HF token from library, files, or environment."""
        logger = logging.getLogger("garak_gui.check_controller")

        if hf_get_token is not None:
            try:
                token = hf_get_token()
                if token and token.strip():
                    logger.debug("Token found from huggingface_hub library")
                    return token.strip()
            except Exception:
                logger.debug("huggingface_hub.get_token() failed, trying other sources")

        token_paths: List[Path] = []
        hf_token_path = os.environ.get("HF_TOKEN_PATH")
        hf_home = os.environ.get("HF_HOME")
        if hf_token_path:
            token_paths.append(Path(hf_token_path).expanduser())
        if hf_home:
            token_paths.append(Path(hf_home).expanduser() / "token")
        token_paths.append(Path.home() / ".cache" / "huggingface" / "token")
        token_paths.append(Path.home() / ".huggingface" / "token")

        _MAX_TOKEN_FILE_SIZE = 1024  # 1KB

        seen: set = set()
        for path in token_paths:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            if not path.exists():
                continue
            try:
                file_size = path.stat().st_size
                if file_size > _MAX_TOKEN_FILE_SIZE:
                    logger.warning(
                        "Token file too large (%d bytes), skipping: %s",
                        file_size,
                        path,
                    )
                    continue
                token = path.read_text().strip()
                if token:
                    logger.debug("Token found from file: %s", path)
                    return token
            except (OSError, PermissionError) as exc:
                logger.debug("Cannot read token file %s: %s", path, exc)
                continue

        for var in ("HF_TOKEN", "HUGGINGFACE_TOKEN"):
            token = os.environ.get(var)
            if token and token.strip():
                logger.debug("Token found from environment variable: %s", var)
                return token.strip()

        return None

    def _clear_check_flag(self) -> None:
        self._check_in_progress = False
        return GLib.SOURCE_REMOVE

    def _update_hf_ui(
        self, success: bool, message: str, instruction_markup: str
    ) -> None:
        if success:
            self._hf_status_label.set_text(message)
            self._reset_style(self._hf_status_label, "status-ok")
            self._hf_instruction.hide()
            self._hf_retry_btn.hide()
            self._step2_next_btn.set_sensitive(True)
            self._on_step2_done(True)
        else:
            self._hf_status_label.set_text(message)
            self._reset_style(self._hf_status_label, "status-fail")
            if instruction_markup:
                self._hf_instruction.set_markup(instruction_markup)
                self._hf_instruction.show()
            self._hf_retry_btn.show()
            self._step2_next_btn.set_sensitive(False)
            self._on_step2_done(False)
        return GLib.SOURCE_REMOVE

    def _on_hf_retry(self, _widget) -> None:
        self.run_hf_check()

    # ── Public accessors ────────────────────────────────────────────

    @property
    def garak_version(self) -> Optional[str]:
        return self._garak_version

    @property
    def hf_username(self) -> Optional[str]:
        return self._hf_username

    @property
    def hf_token(self) -> Optional[str]:
        return self._hf_token

    @property
    def step1_next_btn(self) -> Gtk.Button:
        return self._step1_next_btn

    @property
    def step2_back_btn(self) -> Gtk.Button:
        return self._step2_back_btn

    @property
    def step2_next_btn(self) -> Gtk.Button:
        return self._step2_next_btn

    # ── Utility ─────────────────────────────────────────────────────

    @staticmethod
    def _reset_style(widget: Gtk.Widget, new_class: str) -> None:
        ctx = widget.get_style_context()
        for cls in ("status-ok", "status-fail", "status-pending"):
            ctx.remove_class(cls)
        ctx.add_class(new_class)
