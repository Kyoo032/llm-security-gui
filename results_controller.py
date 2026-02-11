"""Step 7: Results – summary cards, detailed results, export."""

from __future__ import annotations

import logging
from typing import Optional

import gi  # type: ignore
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # type: ignore

from garak_report_parser import GarakReportParser, GarakSummary
from garak_runner import GarakRunResult


class ResultsController:
    """Manages Step 7: displaying test results."""

    def __init__(
        self,
        builder: Gtk.Builder,
        on_new_test: object,
    ) -> None:
        self.builder = builder
        self.logger = logging.getLogger("garak_gui.results_controller")
        self._parser = GarakReportParser()
        self._on_new_test = on_new_test
        self._last_summary: Optional[GarakSummary] = None

        self._build_step7()

    def _build_step7(self) -> None:
        page = self.builder.get_object("step_7_page")
        if page is None:
            return

        title = Gtk.Label(label="Step 7: Test Results")
        title.get_style_context().add_class("step-title")
        title.set_xalign(0)
        page.pack_start(title, False, False, 0)

        # Summary section
        summary_label = Gtk.Label(label="Summary")
        summary_label.get_style_context().add_class("section-title")
        summary_label.set_xalign(0)
        summary_label.set_margin_top(16)
        page.pack_start(summary_label, False, False, 0)

        # Summary cards (4 in a row)
        self._summary_grid = Gtk.Grid()
        self._summary_grid.set_column_spacing(15)
        self._summary_grid.set_row_spacing(0)
        self._summary_grid.set_column_homogeneous(True)
        self._summary_grid.set_margin_top(8)
        self._summary_grid.set_margin_bottom(20)

        self._probes_card = self._create_stat_card("0", "Probes Run", "stat-value-accent")
        self._summary_grid.attach(self._probes_card, 0, 0, 1, 1)

        self._passed_card = self._create_stat_card("0", "Tests Passed", "stat-value-pass")
        self._summary_grid.attach(self._passed_card, 1, 0, 1, 1)

        self._failed_card = self._create_stat_card("0", "Tests Failed", "stat-value-fail")
        self._summary_grid.attach(self._failed_card, 2, 0, 1, 1)

        self._rate_card = self._create_stat_card("0%", "Pass Rate", "stat-value-accent")
        self._summary_grid.attach(self._rate_card, 3, 0, 1, 1)

        page.pack_start(self._summary_grid, False, False, 0)

        # Detailed Results section
        detail_label = Gtk.Label(label="Detailed Results")
        detail_label.get_style_context().add_class("section-title")
        detail_label.set_xalign(0)
        page.pack_start(detail_label, False, False, 0)

        # Scrollable area for result cards
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_margin_top(8)

        self._results_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=0
        )
        scroll.add(self._results_box)
        page.pack_start(scroll, True, True, 0)

        # Action buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_margin_top(16)

        export_btn = Gtk.Button(label="Export Report")
        export_btn.get_style_context().add_class("nav-button-next")
        export_btn.connect("clicked", self._on_export)
        btn_box.pack_start(export_btn, False, False, 0)

        logs_btn = Gtk.Button(label="View Full Logs")
        logs_btn.get_style_context().add_class("nav-button-back")
        logs_btn.connect("clicked", self._on_view_logs)
        btn_box.pack_start(logs_btn, False, False, 0)

        self._new_test_btn = Gtk.Button(label="New Test")
        self._new_test_btn.get_style_context().add_class("nav-button-back")
        self._new_test_btn.connect("clicked", self._on_new_test_clicked)
        btn_box.pack_start(self._new_test_btn, False, False, 0)

        page.pack_start(btn_box, False, False, 0)
        page.show_all()

    def display_results(self, result: GarakRunResult) -> None:
        """Parse and display results from a completed Garak run."""
        if result.report_path:
            summary = self._parser.parse_report(result.report_path)
        else:
            summary = self._parser.parse_stdout(result.stdout)

        self._last_summary = summary
        self._update_summary_cards(summary)
        self._update_detail_cards(summary)

    def _update_summary_cards(self, summary: GarakSummary) -> None:
        self._update_stat_card(
            self._probes_card, str(summary.probes_run), "Probes Run"
        )
        self._update_stat_card(
            self._passed_card, str(summary.total_passed), "Tests Passed"
        )
        self._update_stat_card(
            self._failed_card, str(summary.total_failed), "Tests Failed"
        )
        rate_str = f"{summary.pass_rate * 100:.1f}%"
        self._update_stat_card(self._rate_card, rate_str, "Pass Rate")

    def _update_detail_cards(self, summary: GarakSummary) -> None:
        # Clear existing cards
        for child in self._results_box.get_children():
            self._results_box.remove(child)

        if not summary.by_probe:
            empty = Gtk.Label(label="No probe results to display.")
            empty.get_style_context().add_class("label-muted")
            empty.set_xalign(0)
            empty.set_margin_top(16)
            self._results_box.pack_start(empty, False, False, 0)
            self._results_box.show_all()
            return

        for probe_summary in summary.by_probe:
            card = self._create_result_card(probe_summary)
            self._results_box.pack_start(card, False, False, 0)

        self._results_box.show_all()

    def _create_result_card(self, probe_summary) -> Gtk.Box:
        """Create a result card widget for one probe+detector combo."""
        is_pass = probe_summary.failed == 0
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.get_style_context().add_class("result-card")
        card.get_style_context().add_class(
            "result-card-pass" if is_pass else "result-card-fail"
        )
        card.set_margin_bottom(10)

        # Header row: name + badge
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        name_label = Gtk.Label(
            label=f"{probe_summary.probe} - {probe_summary.detector}"
        )
        name_label.set_xalign(0)
        name_label.set_hexpand(True)
        header.pack_start(name_label, True, True, 0)

        badge = Gtk.Label(label="PASS" if is_pass else "FAIL")
        badge.get_style_context().add_class(
            "badge-pass" if is_pass else "badge-fail"
        )
        header.pack_end(badge, False, False, 0)

        card.pack_start(header, False, False, 0)

        # Summary text
        if is_pass:
            summary_text = (
                f"Model resisted {probe_summary.passed}/{probe_summary.total} "
                f"attempts."
            )
        else:
            summary_text = (
                f"Bypassed in {probe_summary.failed}/{probe_summary.total} "
                f"attempts."
            )

        summary_label = Gtk.Label(label=summary_text)
        summary_label.get_style_context().add_class("label-muted")
        summary_label.set_xalign(0)
        card.pack_start(summary_label, False, False, 0)

        # Expandable details for failures
        if not is_pass and probe_summary.attempts:
            failed_attempts = [
                a for a in probe_summary.attempts if a.passed is False
            ]
            if failed_attempts:
                expander = Gtk.Expander(label="View Details")
                detail_box = Gtk.Box(
                    orientation=Gtk.Orientation.VERTICAL, spacing=4
                )

                for i, attempt in enumerate(failed_attempts[:10]):
                    attempt_text = (
                        f"Attempt #{i + 1}:\n"
                        f"  Prompt: {attempt.prompt[:200]}...\n"
                        f"  Output: {attempt.output[:200]}...\n"
                    )
                    attempt_label = Gtk.Label(label=attempt_text)
                    attempt_label.set_xalign(0)
                    attempt_label.set_line_wrap(True)
                    attempt_label.set_selectable(True)
                    attempt_label.get_style_context().add_class("label-muted")
                    detail_box.pack_start(attempt_label, False, False, 0)

                if len(failed_attempts) > 10:
                    more = Gtk.Label(
                        label=f"... and {len(failed_attempts) - 10} more"
                    )
                    more.get_style_context().add_class("label-muted")
                    more.set_xalign(0)
                    detail_box.pack_start(more, False, False, 0)

                expander.add(detail_box)
                card.pack_start(expander, False, False, 0)

        return card

    @staticmethod
    def _create_stat_card(
        value: str, label_text: str, value_class: str
    ) -> Gtk.Box:
        """Create a summary stat card widget."""
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.get_style_context().add_class("stat-card")
        card.set_halign(Gtk.Align.CENTER)

        value_label = Gtk.Label(label=value)
        value_label.get_style_context().add_class("stat-value")
        value_label.get_style_context().add_class(value_class)
        card.pack_start(value_label, False, False, 0)

        text_label = Gtk.Label(label=label_text)
        text_label.get_style_context().add_class("stat-label")
        card.pack_start(text_label, False, False, 0)

        # Store references for later updates
        card._value_label = value_label
        card._text_label = text_label

        return card

    @staticmethod
    def _update_stat_card(card: Gtk.Box, value: str, label_text: str) -> None:
        """Update a stat card's value and label."""
        if hasattr(card, "_value_label"):
            card._value_label.set_text(value)
        if hasattr(card, "_text_label"):
            card._text_label.set_text(label_text)

    def _on_export(self, _widget: Gtk.Button) -> None:
        self.logger.info("Export report requested")
        # TODO: Implement file chooser dialog for export

    def _on_view_logs(self, _widget: Gtk.Button) -> None:
        self.logger.info("View full logs requested")
        # TODO: Navigate to step 6 to show logs

    def _on_new_test_clicked(self, _widget: Gtk.Button) -> None:
        if callable(self._on_new_test):
            self._on_new_test()

    @property
    def new_test_btn(self) -> Gtk.Button:
        return self._new_test_btn
