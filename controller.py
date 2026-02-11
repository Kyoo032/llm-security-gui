"""Wizard coordinator – delegates to step controllers and manages navigation."""

from __future__ import annotations

import logging
from typing import Dict, Optional

import gi  # type: ignore
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # type: ignore

from check_controller import CheckController
from workspace_controller import WorkspaceController
from run_controller import RunController
from results_controller import ResultsController
from garak_runner import GarakRunResult

STEPS = [
    {"name": "step_1", "label": "1. Framework Setup"},
    {"name": "step_2", "label": "2. Authentication"},
    {"name": "step_3", "label": "3. Model Selection"},
    {"name": "step_4", "label": "4. Probe Selection"},
    {"name": "step_5", "label": "5. Configuration"},
    {"name": "step_6", "label": "6. Run Test"},
    {"name": "step_7", "label": "7. Results"},
]


class PrototypeController:
    """Top-level coordinator for the 7-step wizard flow."""

    def __init__(self, builder: Gtk.Builder) -> None:
        self.builder = builder
        self.logger = logging.getLogger("garak_gui.controller")

        self._step_stack: Optional[Gtk.Stack] = builder.get_object("step_stack")
        self._current_step = 0  # 0-indexed
        self._step_completed = [False] * len(STEPS)
        self._step_rows: Dict[int, Gtk.Box] = {}
        self._step_labels: Dict[int, Gtk.Label] = {}
        self._step_checks: Dict[int, Gtk.Label] = {}

        # Build sidebar
        self._build_sidebar()

        # Sub-controllers
        self._check = CheckController(
            builder,
            on_step1_done=self._on_step1_done,
            on_step2_done=self._on_step2_done,
        )
        self._workspace = WorkspaceController(builder)
        self._run = RunController(
            builder,
            self._workspace,
            on_run_complete=self._on_run_complete,
        )
        self._results = ResultsController(
            builder,
            on_new_test=self._on_new_test,
        )

        # Wire nav buttons
        self._wire_navigation()

        # Status bar
        self._status_dot = builder.get_object("status_dot")
        self._status_text = builder.get_object("status_text")
        self._context_info = builder.get_object("context_info")

        # Start at step 1 and run the check
        self._goto_step(0)
        self._check.run_garak_check()

    # ── Sidebar ─────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        step_list = self.builder.get_object("step_list")
        if step_list is None:
            return

        for i, step in enumerate(STEPS):
            row = Gtk.ListBoxRow()
            row.set_selectable(False)
            row.set_activatable(True)

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.get_style_context().add_class("step-row")

            label = Gtk.Label(label=step["label"])
            label.set_xalign(0)
            label.set_hexpand(True)
            label.get_style_context().add_class("step-label")
            box.pack_start(label, True, True, 0)

            check = Gtk.Label(label="")
            check.get_style_context().add_class("step-check")
            box.pack_end(check, False, False, 0)

            row.add(box)
            row.show_all()

            self._step_rows[i] = box
            self._step_labels[i] = label
            self._step_checks[i] = check

            step_list.add(row)

        step_list.connect("row-activated", self._on_sidebar_row_activated)

    def _on_sidebar_row_activated(
        self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow
    ) -> None:
        index = row.get_index()
        if self._can_navigate_to(index):
            self._goto_step(index)

    def _can_navigate_to(self, step_index: int) -> bool:
        """Check if the user can navigate to a given step."""
        if step_index == 0:
            return True
        # Steps 1-2 must be completed to unlock steps 3+
        if step_index >= 2 and not (
            self._step_completed[0] and self._step_completed[1]
        ):
            return False
        # Step 6 requires model + probes (steps 2-4 complete)
        if step_index == 5:
            model_type, model_name = self._workspace.get_selected_model()
            probes = self._workspace.get_selected_probes()
            if not model_name or not probes:
                return False
        # Step 7 only accessible after run
        if step_index == 6 and not self._step_completed[5]:
            return False
        # All prior steps must be accessible
        for i in range(step_index):
            if i < 2 and not self._step_completed[i]:
                return False
        return True

    def _goto_step(self, step_index: int) -> None:
        """Navigate to a wizard step."""
        self._current_step = step_index
        step_name = STEPS[step_index]["name"]

        if self._step_stack is not None:
            self._step_stack.set_visible_child_name(step_name)

        self._update_sidebar()
        self._update_status_bar()

        # Auto-run checks when entering step 2
        if step_index == 1:
            self._check.run_hf_check()

    def _update_sidebar(self) -> None:
        """Update sidebar visual state."""
        for i in range(len(STEPS)):
            box = self._step_rows.get(i)
            label = self._step_labels.get(i)
            check = self._step_checks.get(i)
            if box is None or label is None or check is None:
                continue

            ctx = box.get_style_context()
            ctx.remove_class("step-row-current")
            ctx.remove_class("step-row-completed")

            label_ctx = label.get_style_context()
            label_ctx.remove_class("step-label-disabled")

            if i == self._current_step:
                ctx.add_class("step-row-current")
                check.set_text("")
            elif self._step_completed[i]:
                ctx.add_class("step-row-completed")
                check.set_text("\u2713")
            elif not self._can_navigate_to(i):
                label_ctx.add_class("step-label-disabled")
                check.set_text("")
            else:
                check.set_text("")

    def _update_status_bar(self) -> None:
        """Update the bottom status bar based on current state."""
        step_index = self._current_step

        if step_index == 0:
            version = self._check.garak_version
            if version:
                self._set_status("ok", "Ready", f"Garak v{version}")
            else:
                self._set_status("pending", "Checking...", "")
        elif step_index == 1:
            username = self._check.hf_username
            version = self._check.garak_version or ""
            if username:
                self._set_status(
                    "ok",
                    "Ready",
                    f"Garak v{version} | HuggingFace Authenticated",
                )
            else:
                self._set_status("pending", "Checking...", f"Garak v{version}")
        elif step_index in (2, 3, 4):
            probe_count = self._workspace.get_selected_probe_count()
            model_type, model_name = self._workspace.get_selected_model()
            target = model_name if model_name else "(none)"
            self._set_status(
                "ok",
                f"{probe_count} probes selected",
                f"Target: {target}",
            )
        elif step_index == 5:
            if self._run.is_running:
                self._set_status("running", "Running...", "")
            else:
                self._set_status("ok", "Ready to run", "")
        elif step_index == 6:
            self._set_status("ok", "Results available", "")

    def _set_status(self, state: str, text: str, context: str) -> None:
        if self._status_dot is not None:
            ctx = self._status_dot.get_style_context()
            for cls in (
                "status-dot-ok",
                "status-dot-fail",
                "status-dot-pending",
                "status-dot-running",
            ):
                ctx.remove_class(cls)
            ctx.add_class(f"status-dot-{state}")
        if self._status_text is not None:
            self._status_text.set_text(text)
        if self._context_info is not None:
            self._context_info.set_text(context)

    # ── Navigation wiring ───────────────────────────────────────────

    def _wire_navigation(self) -> None:
        """Connect all Back/Next button signals."""
        # Step 1 -> Step 2
        self._check.step1_next_btn.connect(
            "clicked", lambda _: self._goto_step(1)
        )
        # Step 2 -> Step 1, Step 3
        self._check.step2_back_btn.connect(
            "clicked", lambda _: self._goto_step(0)
        )
        self._check.step2_next_btn.connect(
            "clicked", lambda _: self._goto_step(2)
        )
        # Step 3 -> Step 2, Step 4
        self._workspace.step3_back_btn.connect(
            "clicked", lambda _: self._goto_step(1)
        )
        self._workspace.step3_next_btn.connect(
            "clicked", lambda _: self._goto_step(3)
        )
        # Step 4 -> Step 3, Step 5
        self._workspace.step4_back_btn.connect(
            "clicked", lambda _: self._goto_step(2)
        )
        self._workspace.step4_next_btn.connect(
            "clicked", lambda _: self._goto_step(4)
        )
        # Step 5 -> Step 4, Step 6 (starts run)
        self._workspace.step5_back_btn.connect(
            "clicked", lambda _: self._goto_step(3)
        )
        self._workspace.step5_next_btn.connect(
            "clicked", self._on_run_test_clicked
        )

    def _on_run_test_clicked(self, _widget: Gtk.Button) -> None:
        """Navigate to Step 6 and start the run."""
        self._goto_step(5)
        self._run.start_run()

    # ── Step completion callbacks ───────────────────────────────────

    def _on_step1_done(self, success: bool) -> None:
        self._step_completed[0] = success
        self._update_sidebar()
        self._update_status_bar()

    def _on_step2_done(self, success: bool) -> None:
        self._step_completed[1] = success
        if success:
            self._workspace.set_hf_username(self._check.hf_username)
        self._update_sidebar()
        self._update_status_bar()

    def _on_run_complete(self, result: GarakRunResult) -> None:
        self._step_completed[5] = True
        self._results.display_results(result)
        self._step_completed[6] = True
        self._update_sidebar()
        # Auto-advance to results
        self._goto_step(6)

    def _on_new_test(self) -> None:
        """Return to step 3 for a new test run."""
        self._step_completed[5] = False
        self._step_completed[6] = False
        self._goto_step(2)
        self._update_sidebar()

    # ── Signal handlers (Glade expects these on the controller) ─────

    def on_main_window_destroy(self, *_args) -> None:
        Gtk.main_quit()
