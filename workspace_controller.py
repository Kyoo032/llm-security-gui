"""Steps 3-5: Model Selection, Probe Selection, Configuration."""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Tuple

import gi  # type: ignore
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # type: ignore

from probes import ProbeManager

# Probe presets: maps preset name -> list of category names to select
PROBE_PRESETS: Dict[str, List[str]] = {
    "Recommended Set": [
        "Prompt Injection",
        "DAN Jailbreaks",
        "Encoding Attacks",
    ],
    "Advanced Threats": [
        "GCG Attacks",
        "Attack Generation",
        "Goal Hijacking",
        "Data Extraction",
    ],
}


class WorkspaceController:
    """Manages Step 3 (Model), Step 4 (Probes), Step 5 (Configuration)."""

    def __init__(self, builder: Gtk.Builder) -> None:
        self.builder = builder
        self.logger = logging.getLogger("garak_gui.workspace_controller")
        self.probe_manager = ProbeManager()

        self._hf_username: Optional[str] = None
        self._probe_checkboxes: Dict[str, Gtk.CheckButton] = {}

        self._build_step3()
        self._build_step4()
        self._build_step5()

    # ── Step 3: Model Selection ─────────────────────────────────────

    def _build_step3(self) -> None:
        page = self.builder.get_object("step_3_page")
        if page is None:
            return

        title = Gtk.Label(label="Step 3: Model Selection")
        title.get_style_context().add_class("step-title")
        title.set_xalign(0)
        page.pack_start(title, False, False, 0)

        # Model Source section
        source_label = Gtk.Label(label="Model Source")
        source_label.get_style_context().add_class("section-title")
        source_label.set_xalign(0)
        source_label.set_margin_top(16)
        page.pack_start(source_label, False, False, 0)

        radio_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        radio_box.set_margin_top(8)
        radio_box.set_margin_bottom(16)

        self._radio_hf = Gtk.RadioButton.new_with_label(None, "HuggingFace Hub")
        self._radio_hf.connect("toggled", self._on_model_source_toggled)
        radio_box.pack_start(self._radio_hf, False, False, 0)

        self._radio_local = Gtk.RadioButton.new_with_label_from_widget(
            self._radio_hf, "Local Endpoint"
        )
        radio_box.pack_start(self._radio_local, False, False, 0)

        page.pack_start(radio_box, False, False, 0)

        # HuggingFace Model section
        hf_section = Gtk.Label(label="HuggingFace Model")
        hf_section.get_style_context().add_class("section-title")
        hf_section.set_xalign(0)
        page.pack_start(hf_section, False, False, 0)

        # Model ID input
        model_label = Gtk.Label(label="Model ID")
        model_label.get_style_context().add_class("label-input")
        model_label.set_xalign(0)
        model_label.set_margin_top(8)
        page.pack_start(model_label, False, False, 0)

        self._model_entry = Gtk.Entry()
        self._model_entry.set_placeholder_text(
            "e.g., meta-llama/Llama-2-7b-chat-hf"
        )
        self._model_entry.set_text("distilgpt2")
        page.pack_start(self._model_entry, False, False, 4)

        # Auth token display
        token_label = Gtk.Label(label="Authentication Token")
        token_label.get_style_context().add_class("label-input")
        token_label.set_xalign(0)
        token_label.set_margin_top(12)
        page.pack_start(token_label, False, False, 0)

        self._token_display = Gtk.Entry()
        self._token_display.set_editable(False)
        self._token_display.set_text("Not authenticated")
        page.pack_start(self._token_display, False, False, 4)

        # Local Endpoint section
        local_section = Gtk.Label(label="Alternative: Local Endpoint")
        local_section.get_style_context().add_class("section-title")
        local_section.set_xalign(0)
        local_section.set_margin_top(24)
        page.pack_start(local_section, False, False, 0)

        endpoint_label = Gtk.Label(label="Endpoint URL")
        endpoint_label.get_style_context().add_class("label-input")
        endpoint_label.set_xalign(0)
        endpoint_label.set_margin_top(8)
        page.pack_start(endpoint_label, False, False, 0)

        self._endpoint_entry = Gtk.Entry()
        self._endpoint_entry.set_placeholder_text(
            "http://localhost:8000/v1/completions"
        )
        self._endpoint_entry.set_sensitive(False)
        page.pack_start(self._endpoint_entry, False, False, 4)

        # Nav buttons
        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav.set_margin_top(24)

        self._step3_back_btn = Gtk.Button(label="\u2190 Back")
        self._step3_back_btn.get_style_context().add_class("nav-button-back")
        nav.pack_start(self._step3_back_btn, False, False, 0)

        self._step3_next_btn = Gtk.Button(label="Next: Select Probes \u2192")
        self._step3_next_btn.get_style_context().add_class("nav-button-next")
        nav.pack_end(self._step3_next_btn, False, False, 0)

        page.pack_start(nav, False, False, 0)
        page.show_all()

    def _on_model_source_toggled(self, radio: Gtk.RadioButton) -> None:
        is_hf = self._radio_hf.get_active()
        self._model_entry.set_sensitive(is_hf)
        self._token_display.set_sensitive(is_hf)
        self._endpoint_entry.set_sensitive(not is_hf)

    def set_hf_username(self, username: Optional[str]) -> None:
        """Update auth display after HF login check passes."""
        self._hf_username = username
        if username:
            self._token_display.set_text(f"Authenticated as {username}")
            ctx = self._token_display.get_style_context()
            ctx.add_class("status-ok")
        else:
            self._token_display.set_text("Not authenticated")

    # ── Step 4: Probe Selection ─────────────────────────────────────

    def _build_step4(self) -> None:
        page = self.builder.get_object("step_4_page")
        if page is None:
            return

        title = Gtk.Label(label="Step 4: Select Probes & Detectors")
        title.get_style_context().add_class("step-title")
        title.set_xalign(0)
        page.pack_start(title, False, False, 0)

        section = Gtk.Label(label="Available Probes (Select multiple)")
        section.get_style_context().add_class("section-title")
        section.set_xalign(0)
        section.set_margin_top(16)
        page.pack_start(section, False, False, 0)

        # Checkbox grid in a scrolled window
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(250)
        scroll.set_propagate_natural_height(True)
        scroll.set_margin_top(8)

        flow = Gtk.FlowBox()
        flow.set_valign(Gtk.Align.START)
        flow.set_max_children_per_line(2)
        flow.set_min_children_per_line(2)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.get_style_context().add_class("checkbox-grid")

        categories = self.probe_manager.get_categories()
        for category_name in sorted(categories.keys()):
            check = Gtk.CheckButton(label=category_name)
            check.set_margin_start(8)
            check.set_margin_end(8)
            check.set_margin_top(4)
            check.set_margin_bottom(4)
            self._probe_checkboxes[category_name] = check
            flow.add(check)

        scroll.add(flow)
        page.pack_start(scroll, False, False, 0)

        # Quick Presets
        presets_label = Gtk.Label(label="Quick Presets")
        presets_label.get_style_context().add_class("section-title")
        presets_label.set_xalign(0)
        presets_label.set_margin_top(20)
        page.pack_start(presets_label, False, False, 0)

        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        preset_box.set_margin_top(8)

        select_all_btn = Gtk.Button(label="Select All")
        select_all_btn.get_style_context().add_class("preset-button")
        select_all_btn.connect("clicked", self._on_select_all)
        preset_box.pack_start(select_all_btn, False, False, 0)

        deselect_all_btn = Gtk.Button(label="Deselect All")
        deselect_all_btn.get_style_context().add_class("preset-button")
        deselect_all_btn.connect("clicked", self._on_deselect_all)
        preset_box.pack_start(deselect_all_btn, False, False, 0)

        recommended_btn = Gtk.Button(label="Recommended Set")
        recommended_btn.get_style_context().add_class("preset-button")
        recommended_btn.connect("clicked", self._on_preset_recommended)
        preset_box.pack_start(recommended_btn, False, False, 0)

        advanced_btn = Gtk.Button(label="Advanced Threats")
        advanced_btn.get_style_context().add_class("preset-button")
        advanced_btn.connect("clicked", self._on_preset_advanced)
        preset_box.pack_start(advanced_btn, False, False, 0)

        page.pack_start(preset_box, False, False, 0)

        # Nav buttons
        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav.set_margin_top(24)

        self._step4_back_btn = Gtk.Button(label="\u2190 Back")
        self._step4_back_btn.get_style_context().add_class("nav-button-back")
        nav.pack_start(self._step4_back_btn, False, False, 0)

        self._step4_next_btn = Gtk.Button(
            label="Next: Configure Settings \u2192"
        )
        self._step4_next_btn.get_style_context().add_class("nav-button-next")
        nav.pack_end(self._step4_next_btn, False, False, 0)

        page.pack_start(nav, False, False, 0)
        page.show_all()

    def _on_select_all(self, _btn: Gtk.Button) -> None:
        for check in self._probe_checkboxes.values():
            check.set_active(True)

    def _on_deselect_all(self, _btn: Gtk.Button) -> None:
        for check in self._probe_checkboxes.values():
            check.set_active(False)

    def _on_preset_recommended(self, _btn: Gtk.Button) -> None:
        self._apply_preset("Recommended Set")

    def _on_preset_advanced(self, _btn: Gtk.Button) -> None:
        self._apply_preset("Advanced Threats")

    def _apply_preset(self, preset_name: str) -> None:
        categories = PROBE_PRESETS.get(preset_name, [])
        for name, check in self._probe_checkboxes.items():
            check.set_active(name in categories)

    # ── Step 5: Configuration ───────────────────────────────────────

    # Garak parameter limits
    _GENERATIONS_MIN = 1
    _GENERATIONS_MAX = 50
    _GENERATIONS_DEFAULT = 1
    _GENERATIONS_WARN = 10

    _TEMPERATURE_MIN = 0.0
    _TEMPERATURE_MAX = 2.0
    _TEMPERATURE_DEFAULT = 0.7

    _MAX_TOKENS_MIN = 16
    _MAX_TOKENS_MAX = 2048
    _MAX_TOKENS_DEFAULT = 512
    _MAX_TOKENS_WARN = 1024

    def _build_step5(self) -> None:
        page = self.builder.get_object("step_5_page")
        if page is None:
            return

        title = Gtk.Label(label="Step 5: Configure Probe Settings")
        title.get_style_context().add_class("step-title")
        title.set_xalign(0)
        page.pack_start(title, False, False, 0)

        # Defaults explanation
        defaults_note = Gtk.Label()
        defaults_note.set_markup(
            "<small>Defaults are tuned for low-VRAM GPUs (4 GB). "
            "Higher values increase scan time, memory usage, and API costs.</small>"
        )
        defaults_note.set_xalign(0)
        defaults_note.set_line_wrap(True)
        defaults_note.set_margin_top(8)
        defaults_note.get_style_context().add_class("label-muted")
        page.pack_start(defaults_note, False, False, 0)

        # Generation Parameters section
        gen_label = Gtk.Label(label="Generation Parameters")
        gen_label.get_style_context().add_class("section-title")
        gen_label.set_xalign(0)
        gen_label.set_margin_top(16)
        page.pack_start(gen_label, False, False, 0)

        gen_grid = Gtk.Grid()
        gen_grid.set_column_spacing(16)
        gen_grid.set_row_spacing(4)
        gen_grid.set_margin_top(8)

        row = 0

        # Generations per prompt
        gens_label = Gtk.Label(
            label=f"Generations per Prompt ({self._GENERATIONS_MIN}"
            f"-{self._GENERATIONS_MAX}, default: {self._GENERATIONS_DEFAULT})"
        )
        gens_label.get_style_context().add_class("label-input")
        gens_label.set_xalign(0)
        gens_label.set_hexpand(True)
        gen_grid.attach(gens_label, 0, row, 1, 1)

        self._generations_spin = Gtk.SpinButton.new_with_range(
            self._GENERATIONS_MIN, self._GENERATIONS_MAX, 1
        )
        self._generations_spin.set_value(self._GENERATIONS_DEFAULT)
        self._generations_spin.set_width_chars(8)
        self._generations_spin.set_numeric(True)
        self._generations_spin.set_hexpand(False)
        self._generations_spin.connect("value-changed", self._on_generations_changed)
        gen_grid.attach(self._generations_spin, 1, row, 1, 1)

        row += 1
        gens_hint = Gtk.Label()
        gens_hint.set_markup(
            "<small>How many times Garak repeats each probe. "
            "Default 1 is enough for a quick scan.</small>"
        )
        gens_hint.set_xalign(0)
        gens_hint.set_line_wrap(True)
        gens_hint.get_style_context().add_class("label-muted")
        gen_grid.attach(gens_hint, 0, row, 2, 1)

        row += 1
        self._generations_warning = Gtk.Label()
        self._generations_warning.set_xalign(0)
        self._generations_warning.set_line_wrap(True)
        self._generations_warning.set_no_show_all(True)
        self._generations_warning.get_style_context().add_class("warning-label")
        gen_grid.attach(self._generations_warning, 0, row, 2, 1)

        row += 1

        # Temperature
        temp_label = Gtk.Label(
            label=f"Temperature ({self._TEMPERATURE_MIN:.1f}"
            f"-{self._TEMPERATURE_MAX:.1f}, default: {self._TEMPERATURE_DEFAULT})"
        )
        temp_label.get_style_context().add_class("label-input")
        temp_label.set_xalign(0)
        temp_label.set_margin_top(8)
        gen_grid.attach(temp_label, 0, row, 1, 1)

        self._temperature_spin = Gtk.SpinButton.new_with_range(
            self._TEMPERATURE_MIN, self._TEMPERATURE_MAX, 0.1
        )
        self._temperature_spin.set_digits(1)
        self._temperature_spin.set_value(self._TEMPERATURE_DEFAULT)
        self._temperature_spin.set_width_chars(8)
        self._temperature_spin.set_numeric(True)
        self._temperature_spin.set_hexpand(False)
        gen_grid.attach(self._temperature_spin, 1, row, 1, 1)

        row += 1
        temp_hint = Gtk.Label()
        temp_hint.set_markup(
            "<small>Controls randomness. 0.7 balances variety and coherence.</small>"
        )
        temp_hint.set_xalign(0)
        temp_hint.set_line_wrap(True)
        temp_hint.get_style_context().add_class("label-muted")
        gen_grid.attach(temp_hint, 0, row, 2, 1)

        row += 1

        # Max tokens
        tokens_label = Gtk.Label(
            label=f"Max Tokens ({self._MAX_TOKENS_MIN}"
            f"-{self._MAX_TOKENS_MAX}, default: {self._MAX_TOKENS_DEFAULT})"
        )
        tokens_label.get_style_context().add_class("label-input")
        tokens_label.set_xalign(0)
        tokens_label.set_margin_top(8)
        gen_grid.attach(tokens_label, 0, row, 1, 1)

        self._max_tokens_spin = Gtk.SpinButton.new_with_range(
            self._MAX_TOKENS_MIN, self._MAX_TOKENS_MAX, 16
        )
        self._max_tokens_spin.set_value(self._MAX_TOKENS_DEFAULT)
        self._max_tokens_spin.set_width_chars(8)
        self._max_tokens_spin.set_numeric(True)
        self._max_tokens_spin.set_hexpand(False)
        self._max_tokens_spin.connect("value-changed", self._on_max_tokens_changed)
        gen_grid.attach(self._max_tokens_spin, 1, row, 1, 1)

        row += 1
        tokens_hint = Gtk.Label()
        tokens_hint.set_markup(
            "<small>Max response length per generation. "
            "512 is enough for most probes without excessive VRAM use.</small>"
        )
        tokens_hint.set_xalign(0)
        tokens_hint.set_line_wrap(True)
        tokens_hint.get_style_context().add_class("label-muted")
        gen_grid.attach(tokens_hint, 0, row, 2, 1)

        row += 1
        self._max_tokens_warning = Gtk.Label()
        self._max_tokens_warning.set_xalign(0)
        self._max_tokens_warning.set_line_wrap(True)
        self._max_tokens_warning.set_no_show_all(True)
        self._max_tokens_warning.get_style_context().add_class("warning-label")
        gen_grid.attach(self._max_tokens_warning, 0, row, 2, 1)

        page.pack_start(gen_grid, False, False, 0)

        # Probe-Specific Options section
        opts_label = Gtk.Label(label="Probe-Specific Options")
        opts_label.get_style_context().add_class("section-title")
        opts_label.set_xalign(0)
        opts_label.set_margin_top(24)
        page.pack_start(opts_label, False, False, 0)

        opts_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        opts_box.set_margin_top(8)

        self._verbose_check = Gtk.CheckButton(label="Enable verbose logging")
        self._verbose_check.set_active(True)
        opts_box.pack_start(self._verbose_check, False, False, 0)

        self._intermediate_check = Gtk.CheckButton(
            label="Save intermediate outputs"
        )
        opts_box.pack_start(self._intermediate_check, False, False, 0)

        self._parallel_check = Gtk.CheckButton(label="Use parallel execution")
        self._parallel_check.set_active(True)
        opts_box.pack_start(self._parallel_check, False, False, 0)

        page.pack_start(opts_box, False, False, 0)

        # Output Configuration section
        out_label = Gtk.Label(label="Output Configuration")
        out_label.get_style_context().add_class("section-title")
        out_label.set_xalign(0)
        out_label.set_margin_top(24)
        page.pack_start(out_label, False, False, 0)

        out_grid = Gtk.Grid()
        out_grid.set_column_spacing(16)
        out_grid.set_row_spacing(12)
        out_grid.set_margin_top(8)

        fmt_label = Gtk.Label(label="Report Format")
        fmt_label.get_style_context().add_class("label-input")
        fmt_label.set_xalign(0)
        out_grid.attach(fmt_label, 0, 0, 1, 1)

        self._format_combo = Gtk.ComboBoxText()
        for fmt in ("JSON", "HTML", "CSV", "All Formats"):
            self._format_combo.append_text(fmt)
        self._format_combo.set_active(1)  # Default: HTML
        out_grid.attach(self._format_combo, 1, 0, 1, 1)

        dir_label = Gtk.Label(label="Output Directory")
        dir_label.get_style_context().add_class("label-input")
        dir_label.set_xalign(0)
        out_grid.attach(dir_label, 0, 1, 1, 1)

        self._output_dir_entry = Gtk.Entry()
        self._output_dir_entry.set_text("./garak_reports/")
        self._output_dir_entry.set_hexpand(True)
        out_grid.attach(self._output_dir_entry, 1, 1, 1, 1)

        page.pack_start(out_grid, False, False, 0)

        # Nav buttons
        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav.set_margin_top(24)

        self._step5_back_btn = Gtk.Button(label="\u2190 Back")
        self._step5_back_btn.get_style_context().add_class("nav-button-back")
        nav.pack_start(self._step5_back_btn, False, False, 0)

        self._step5_next_btn = Gtk.Button(label="Next: Run Test \u2192")
        self._step5_next_btn.get_style_context().add_class("nav-button-next")
        nav.pack_end(self._step5_next_btn, False, False, 0)

        page.pack_start(nav, False, False, 0)
        page.show_all()

    # ── Value-changed warnings ─────────────────────────────────────

    def _on_generations_changed(self, spin: Gtk.SpinButton) -> None:
        value = int(spin.get_value())
        if value > self._GENERATIONS_WARN:
            self._generations_warning.set_markup(
                f"<small>\u26a0 High value ({value}). Each generation runs "
                f"every selected probe again, multiplying scan time, "
                f"VRAM usage, and API calls. "
                f"Consider {self._GENERATIONS_DEFAULT}-"
                f"{self._GENERATIONS_WARN} unless you need "
                f"statistical confidence.</small>"
            )
            self._generations_warning.show()
        else:
            self._generations_warning.hide()

    def _on_max_tokens_changed(self, spin: Gtk.SpinButton) -> None:
        value = int(spin.get_value())
        if value > self._MAX_TOKENS_WARN:
            self._max_tokens_warning.set_markup(
                f"<small>\u26a0 High value ({value}). Larger responses "
                f"consume more VRAM and increase inference time per "
                f"generation. On 4 GB GPUs this may cause out-of-memory "
                f"errors. {self._MAX_TOKENS_DEFAULT} tokens is enough "
                f"for most probes.</small>"
            )
            self._max_tokens_warning.show()
        else:
            self._max_tokens_warning.hide()

    # ── Public accessors ────────────────────────────────────────────

    def get_selected_model(self) -> Tuple[str, str]:
        """Return (model_type, model_name_or_url)."""
        if self._radio_hf.get_active():
            return ("huggingface", self._model_entry.get_text().strip())
        return ("local", self._endpoint_entry.get_text().strip())

    def get_selected_probes(self) -> List[str]:
        """Return list of selected probe category names."""
        return [
            name
            for name, check in self._probe_checkboxes.items()
            if check.get_active()
        ]

    def get_selected_probe_count(self) -> int:
        return len(self.get_selected_probes())

    def get_run_settings(self) -> Dict:
        """Return all configuration settings for the run, clamped to safe ranges."""
        generations = max(
            self._GENERATIONS_MIN,
            min(self._GENERATIONS_MAX, int(self._generations_spin.get_value())),
        )
        temperature = max(
            self._TEMPERATURE_MIN,
            min(self._TEMPERATURE_MAX, round(self._temperature_spin.get_value(), 1)),
        )
        max_tokens = max(
            self._MAX_TOKENS_MIN,
            min(self._MAX_TOKENS_MAX, int(self._max_tokens_spin.get_value())),
        )
        return {
            "generations": generations,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "verbose": self._verbose_check.get_active(),
            "save_intermediate": self._intermediate_check.get_active(),
            "parallel": self._parallel_check.get_active(),
            "report_format": self._format_combo.get_active_text() or "HTML",
            "output_dir": self._output_dir_entry.get_text().strip(),
        }

    # ── Nav button accessors ────────────────────────────────────────

    @property
    def step3_back_btn(self) -> Gtk.Button:
        return self._step3_back_btn

    @property
    def step3_next_btn(self) -> Gtk.Button:
        return self._step3_next_btn

    @property
    def step4_back_btn(self) -> Gtk.Button:
        return self._step4_back_btn

    @property
    def step4_next_btn(self) -> Gtk.Button:
        return self._step4_next_btn

    @property
    def step5_back_btn(self) -> Gtk.Button:
        return self._step5_back_btn

    @property
    def step5_next_btn(self) -> Gtk.Button:
        return self._step5_next_btn
