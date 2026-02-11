"""Step 6: Run Test – Garak execution with live output and progress."""

from __future__ import annotations

import logging
import time
from typing import Callable, Dict, List, Optional

import gi  # type: ignore
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # type: ignore

from garak_runner import GarakRunConfig, GarakRunResult, GarakRunner
from workspace_controller import WorkspaceController


class RunController:
    """Manages Step 6: executing Garak and displaying progress."""

    def __init__(
        self,
        builder: Gtk.Builder,
        workspace: WorkspaceController,
        on_run_complete: Callable[[GarakRunResult], None],
    ) -> None:
        self.builder = builder
        self.logger = logging.getLogger("garak_gui.run_controller")
        self._workspace = workspace
        self._runner = GarakRunner()
        self._on_run_complete = on_run_complete

        self._run_active = False
        self._started_at = 0.0
        self._timer_id: Optional[int] = None

        self._build_step6()

    def _build_step6(self) -> None:
        page = self.builder.get_object("step_6_page")
        if page is None:
            return

        title = Gtk.Label(label="Step 6: Running Security Assessment")
        title.get_style_context().add_class("step-title")
        title.set_xalign(0)
        page.pack_start(title, False, False, 0)

        # Progress section
        progress_label = Gtk.Label(label="Progress")
        progress_label.get_style_context().add_class("section-title")
        progress_label.set_xalign(0)
        progress_label.set_margin_top(16)
        page.pack_start(progress_label, False, False, 0)

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_show_text(True)
        self._progress_bar.set_text("Idle")
        self._progress_bar.set_fraction(0.0)
        self._progress_bar.set_margin_top(8)
        page.pack_start(self._progress_bar, False, False, 0)

        self._progress_detail = Gtk.Label(label="")
        self._progress_detail.get_style_context().add_class("label-muted")
        self._progress_detail.set_xalign(0)
        self._progress_detail.set_margin_top(4)
        page.pack_start(self._progress_detail, False, False, 0)

        self._eta_label = Gtk.Label(label="")
        self._eta_label.get_style_context().add_class("label-muted")
        self._eta_label.set_xalign(0)
        page.pack_start(self._eta_label, False, False, 0)

        # Live Output section
        output_label = Gtk.Label(label="Live Output")
        output_label.get_style_context().add_class("section-title")
        output_label.set_xalign(0)
        output_label.set_margin_top(20)
        page.pack_start(output_label, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(300)
        scroll.set_vexpand(True)
        scroll.set_margin_top(8)

        self._output_view = Gtk.TextView()
        self._output_view.set_editable(False)
        self._output_view.set_cursor_visible(False)
        self._output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._output_view.set_left_margin(10)
        self._output_view.set_right_margin(10)
        self._output_view.set_top_margin(8)
        self._output_view.set_bottom_margin(8)
        self._output_view.get_style_context().add_class("garak-output")

        self._output_buffer = self._output_view.get_buffer()
        scroll.add(self._output_view)
        page.pack_start(scroll, True, True, 0)

        # Cancel button
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_margin_top(16)

        self._cancel_btn = Gtk.Button(label="Cancel Run")
        self._cancel_btn.get_style_context().add_class("nav-button-back")
        self._cancel_btn.set_sensitive(False)
        self._cancel_btn.connect("clicked", self._on_cancel_clicked)
        btn_box.pack_start(self._cancel_btn, False, False, 0)

        page.pack_start(btn_box, False, False, 0)
        page.show_all()

    def start_run(self) -> None:
        """Gather config from workspace and start Garak execution."""
        if self._run_active:
            return

        model_type, model_name = self._workspace.get_selected_model()
        probes = self._workspace.get_selected_probes()
        settings = self._workspace.get_run_settings()

        if not model_name:
            self._append_output("[ERROR] No model selected.\n")
            return
        if not probes:
            self._append_output("[ERROR] No probes selected.\n")
            return

        # Map probe category names to garak probe module names
        probe_mapping = self._map_probe_names(probes)

        config = GarakRunConfig(
            model_type=model_type,
            model_name=model_name,
            probes=probe_mapping,
            generations=settings["generations"],
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"],
            verbose=settings["verbose"],
            parallel=settings["parallel"],
            output_dir=settings["output_dir"],
        )

        self._run_active = True
        self._started_at = time.monotonic()
        self._cancel_btn.set_sensitive(True)
        self._output_buffer.set_text("")

        cmd_str = " ".join(self._runner.build_command(config))
        self._append_output(f"$ {cmd_str}\n\n")

        self._progress_bar.set_fraction(0.0)
        self._progress_bar.set_text("Starting...")
        self._progress_detail.set_text(
            f"Running {len(probe_mapping)} probe(s) on {model_name}"
        )

        # Start elapsed timer
        self._timer_id = GLib.timeout_add(1000, self._update_elapsed)

        self._runner.run(
            config,
            on_stdout_line=lambda line: GLib.idle_add(self._on_stdout, line),
            on_stderr_line=lambda line: GLib.idle_add(self._on_stderr, line),
            on_complete=lambda result: GLib.idle_add(self._on_complete, result),
        )

    @staticmethod
    def _map_probe_names(categories: List[str]) -> List[str]:
        """Map user-facing category names to garak probe module names."""
        mapping: Dict[str, str] = {
            "DAN Jailbreaks": "dan",
            "Encoding Attacks": "encoding",
            "Prompt Injection": "promptinject",
            "LMRC Risk Cards": "lmrc",
            "Attack Generation": "atkgen",
            "GCG Attacks": "gcg",
            "Multilingual Attacks": "encoding",
            "Refusal Bypass": "dan",
            "Goal Hijacking": "promptinject",
            "RAG Poisoning": "promptinject",
            "Data Extraction": "promptinject",
        }
        seen = set()
        result = []
        for cat in categories:
            probe = mapping.get(cat, cat.lower().replace(" ", ""))
            if probe not in seen:
                seen.add(probe)
                result.append(probe)
        return result

    def _on_stdout(self, line: str) -> None:
        self._append_output(line + "\n")
        self._auto_scroll()

        # Update progress from output hints
        if ": PASS" in line or ": FAIL" in line:
            self._progress_bar.pulse()
        return GLib.SOURCE_REMOVE

    def _on_stderr(self, line: str) -> None:
        self._append_output(f"[stderr] {line}\n")
        self._auto_scroll()
        return GLib.SOURCE_REMOVE

    def _on_complete(self, result: GarakRunResult) -> None:
        self._run_active = False
        self._cancel_btn.set_sensitive(False)

        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

        elapsed = time.monotonic() - self._started_at
        elapsed_str = self._format_duration(elapsed)

        if result.error:
            self._append_output(f"\n[ERROR] {result.error}\n")
            self._progress_bar.set_fraction(0.0)
            self._progress_bar.set_text("Failed")
        elif result.success:
            self._progress_bar.set_fraction(1.0)
            self._progress_bar.set_text("Complete")
            self._append_output(f"\nCompleted in {elapsed_str}\n")
        else:
            self._progress_bar.set_fraction(1.0)
            self._progress_bar.set_text(f"Finished (exit code {result.return_code})")
            self._append_output(
                f"\nFinished with exit code {result.return_code} in {elapsed_str}\n"
            )

        self._progress_detail.set_text(f"Elapsed: {elapsed_str}")
        self._eta_label.set_text("")
        self._on_run_complete(result)
        return GLib.SOURCE_REMOVE

    def _on_cancel_clicked(self, _widget: Gtk.Button) -> None:
        if self._run_active:
            self._append_output("\n[CANCELING...]\n")
            self._runner.cancel()

    def _update_elapsed(self) -> bool:
        if not self._run_active:
            return False
        elapsed = time.monotonic() - self._started_at
        self._eta_label.set_text(f"Elapsed: {self._format_duration(elapsed)}")
        return True

    def _append_output(self, text: str) -> None:
        end_iter = self._output_buffer.get_end_iter()
        self._output_buffer.insert(end_iter, text)

        # Limit buffer size to avoid memory issues
        line_count = self._output_buffer.get_line_count()
        if line_count > 10000:
            start = self._output_buffer.get_start_iter()
            cutoff = self._output_buffer.get_iter_at_line(line_count - 8000)
            self._output_buffer.delete(start, cutoff)

    def _auto_scroll(self) -> None:
        end_mark = self._output_buffer.get_insert()
        self._output_buffer.place_cursor(self._output_buffer.get_end_iter())
        self._output_view.scroll_mark_onscreen(end_mark)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total = max(0, int(seconds))
        mins, secs = divmod(total, 60)
        return f"{mins:02d}:{secs:02d}"

    @property
    def is_running(self) -> bool:
        return self._run_active
