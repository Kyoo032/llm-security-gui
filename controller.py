"""Signal handlers for the GTK prototype shell."""

from __future__ import annotations

from collections import deque
import logging
import os
import threading
import time
from pathlib import Path
from typing import Callable, Deque, Dict, List, Optional, Tuple

from gi.repository import GLib, Gtk  # type: ignore

from api_handler import HuggingFaceAPIHandler
from probes import ProbeManager
from payloads import PayloadManager
from compatibility import (
    PROBE_PAYLOAD_COMPATIBILITY,
    ALWAYS_ENABLED_CATEGORIES,
    MODEL_WEIGHT,
    PAYLOAD_WARN_THRESHOLDS,
)

try:
    from huggingface_hub import get_token as hf_get_token
except Exception:
    hf_get_token = None


class PrototypeController:
    """Controller for probe/payload prototype interactions."""

    def __init__(self, builder):
        self.builder = builder
        self.probe_manager = ProbeManager()
        self.payload_manager = PayloadManager()
        self.logger = logging.getLogger("gtk_shell.controller")
        self._probe_index: Dict[str, Dict] = {}
        self._payload_index: Dict[str, Dict] = {}
        self._payload_store: Optional[Gtk.TreeStore] = None
        self._run_queue: Deque[Tuple[str, str]] = deque()
        self._run_total = 0
        self._run_completed = 0
        self._run_started_at = 0.0
        self._run_source_id: Optional[int] = None
        self._run_active = False
        self._cancel_requested = False
        self._probe_search_text = ""
        self._payload_search_text = ""
        self._selected_model: str = ""
        self._check_in_progress = False

        self._setup_navigation()
        self._build_check_page()
        self._run_api_check()

        self._normalize_detail_labels()
        self._setup_probe_tree()
        self._setup_payload_tree()
        self._configure_tree_selections()
        self._load_probe_tree()
        self._load_payload_tree()
        self._setup_model_combo()
        self._set_progress_idle()
        self._set_status(
            f"Loaded {len(self._probe_index)} probes and "
            f"{len(self._payload_index)} payloads"
        )

    # ── Navigation + API check ────────────────────────────────────────

    def _setup_navigation(self) -> None:
        self.main_stack = self.builder.get_object("main_stack")
        if self.main_stack is None:
            self.logger.warning(
                "main_stack widget not found; API check screen will not be shown"
            )
            return
        self.main_stack.set_visible_child_name("check")

    def _build_check_page(self) -> None:
        check_page = self.builder.get_object("check_page")
        if check_page is None:
            return

        # Outer centering box
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_valign(Gtk.Align.CENTER)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_vexpand(True)

        # Title
        title = Gtk.Label(label="LLM Red Team")
        title.get_style_context().add_class("check-title")
        outer.pack_start(title, False, False, 0)

        # Subtitle
        subtitle = Gtk.Label(label="Security Testing Toolkit")
        subtitle.get_style_context().add_class("check-subtitle")
        subtitle.set_margin_bottom(32)
        outer.pack_start(subtitle, False, False, 4)

        # --- HuggingFace API row ---
        hf_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hf_row.get_style_context().add_class("check-api-row")
        hf_row.set_halign(Gtk.Align.CENTER)

        hf_label = Gtk.Label(label="HuggingFace API")
        hf_label.get_style_context().add_class("check-api-label")
        hf_row.pack_start(hf_label, False, False, 0)

        self._hf_status_label = Gtk.Label(label="Checking...")
        self._hf_status_label.get_style_context().add_class("check-status-pending")
        hf_row.pack_start(self._hf_status_label, False, False, 0)

        outer.pack_start(hf_row, False, False, 4)

        # --- OpenAI API row ---
        oai_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        oai_row.get_style_context().add_class("check-api-row")
        oai_row.set_halign(Gtk.Align.CENTER)

        oai_label = Gtk.Label(label="OpenAI API")
        oai_label.get_style_context().add_class("check-api-label")
        oai_row.pack_start(oai_label, False, False, 0)

        oai_status = Gtk.Label(label="Coming Soon")
        oai_status.get_style_context().add_class("check-coming-soon")
        oai_row.pack_start(oai_status, False, False, 0)

        outer.pack_start(oai_row, False, False, 4)

        # --- Instruction label (hidden by default) ---
        self._check_instruction = Gtk.Label()
        self._check_instruction.get_style_context().add_class("check-instruction")
        self._check_instruction.set_markup(
            "Run <b>hf auth login</b> in your terminal, then click Retry"
        )
        self._check_instruction.set_no_show_all(True)
        self._check_instruction.hide()
        self._check_instruction.set_margin_top(16)
        outer.pack_start(self._check_instruction, False, False, 0)

        # --- Button box ---
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(24)

        self._continue_btn = Gtk.Button(label="Continue")
        self._continue_btn.get_style_context().add_class("check-continue-btn")
        self._continue_btn.set_sensitive(False)
        self._continue_btn.connect("clicked", self._on_check_continue_clicked)
        btn_box.pack_start(self._continue_btn, False, False, 0)

        self._retry_btn = Gtk.Button(label="Retry")
        self._retry_btn.get_style_context().add_class("check-retry-btn")
        self._retry_btn.connect("clicked", self._on_check_retry_clicked)
        btn_box.pack_start(self._retry_btn, False, False, 0)

        outer.pack_start(btn_box, False, False, 0)

        check_page.pack_start(outer, True, True, 0)
        check_page.show_all()

    def _detect_hf_token(self) -> Optional[str]:
        # Method 1: huggingface_hub library
        if hf_get_token is not None:
            try:
                token = hf_get_token()
                if token and token.strip():
                    return token.strip()
            except Exception:
                pass

        # Method 2: Direct file reads, including modern Hugging Face paths.
        token_paths: List[Path] = []
        hf_token_path = os.environ.get("HF_TOKEN_PATH")
        hf_home = os.environ.get("HF_HOME")
        if hf_token_path:
            token_paths.append(Path(hf_token_path).expanduser())
        if hf_home:
            token_paths.append(Path(hf_home).expanduser() / "token")
        token_paths.append(Path.home() / ".cache" / "huggingface" / "token")
        token_paths.append(Path.home() / ".huggingface" / "token")

        seen_paths = set()
        for token_path in token_paths:
            path_key = str(token_path)
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)
            if not token_path.exists():
                continue
            try:
                token = token_path.read_text().strip()
                if token:
                    return token
            except Exception:
                continue

        # Method 3-4: Environment variables
        for var in ("HF_TOKEN", "HUGGINGFACE_TOKEN"):
            token = os.environ.get(var)
            if token and token.strip():
                return token.strip()

        return None

    def _run_api_check(self) -> None:
        if self._check_in_progress:
            return
        token = self._detect_hf_token()
        if not token:
            self._update_check_ui(False, "No token found", True)
            return

        self._check_in_progress = True

        def _validate() -> None:
            try:
                handler = HuggingFaceAPIHandler(token)
                ok, message = handler.validate_key()
                GLib.idle_add(self._update_check_ui, ok, message, not ok)
            finally:
                GLib.idle_add(self._clear_check_in_progress)

        threading.Thread(target=_validate, daemon=True).start()

    def _clear_check_in_progress(self) -> None:
        self._check_in_progress = False
        return GLib.SOURCE_REMOVE

    def _reset_hf_status_classes(self) -> None:
        ctx = self._hf_status_label.get_style_context()
        for cls in ("check-status-ok", "check-status-fail", "check-status-pending"):
            ctx.remove_class(cls)

    def _update_check_ui(self, success: bool, message: str, show_instruction: bool) -> None:
        self._reset_hf_status_classes()
        ctx = self._hf_status_label.get_style_context()

        if success:
            ctx.add_class("check-status-ok")
            self._hf_status_label.set_text(message)
            self._continue_btn.set_sensitive(True)
            self._check_instruction.hide()
        else:
            ctx.add_class("check-status-fail")
            self._hf_status_label.set_text(message)
            self._continue_btn.set_sensitive(False)
            if show_instruction:
                self._check_instruction.show()
        return GLib.SOURCE_REMOVE

    def _on_check_continue_clicked(self, _widget) -> None:
        if self.main_stack is not None:
            self.main_stack.set_visible_child_name("workspace")

    def _on_check_retry_clicked(self, _widget) -> None:
        self._reset_hf_status_classes()
        self._hf_status_label.get_style_context().add_class("check-status-pending")
        self._hf_status_label.set_text("Checking...")
        self._continue_btn.set_sensitive(False)
        self._check_instruction.hide()
        self._run_api_check()

    # ── Utility helpers ──────────────────────────────────────────────

    def _set_status(self, message: str) -> None:
        label = self.builder.get_object("status_label")
        if label is not None:
            label.set_text(message)

    def _safe_ui_action(self, context: str, action: Callable[[], None]) -> None:
        """Prevent callback exceptions from taking down the prototype session."""
        try:
            action()
        except Exception:
            self.logger.exception("Unhandled UI error during %s", context)
            self._set_status(
                "Interaction error. Check logs/gtk_shell.log"
            )

    def _set_eta(self, text: str) -> None:
        label = self.builder.get_object("eta_label")
        if label is not None:
            label.set_text(text)

    def _set_progress(self, fraction: float, text: str) -> None:
        progress = self.builder.get_object("run_progress_bar")
        if progress is not None:
            progress.set_show_text(True)
            progress.set_fraction(max(0.0, min(1.0, fraction)))
            progress.set_text(text)

    def _normalize_detail_labels(self) -> None:
        for widget_id in (
            "tab_general_content",
            "tab_packing_content",
            "tab_common_content",
            "tab_signals_content",
        ):
            label = self.builder.get_object(widget_id)
            if label is not None:
                label.set_xalign(0.0)
                label.set_line_wrap(True)
                label.set_selectable(True)

    # ── Tree setup ───────────────────────────────────────────────────

    def _setup_probe_tree(self) -> None:
        """Set up probe tree with a single text column (no checkboxes)."""
        tree = self.builder.get_object("workspace_tree")
        if tree is None:
            return
        for col in tree.get_columns():
            tree.remove_column(col)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Probes", renderer, text=0)
        tree.append_column(column)

    def _setup_payload_tree(self) -> None:
        """Set up payload tree with checkbox toggle + text columns."""
        tree = self.builder.get_object("widget_tree_view")
        if tree is None:
            return
        for col in tree.get_columns():
            tree.remove_column(col)

        # Checkbox column (bound to store column 0 = checked bool)
        toggle_renderer = Gtk.CellRendererToggle()
        toggle_renderer.connect("toggled", self._on_payload_toggled)
        toggle_col = Gtk.TreeViewColumn("", toggle_renderer)
        toggle_col.set_cell_data_func(toggle_renderer, self._payload_toggle_data_func)
        tree.append_column(toggle_col)

        # Text column (bound to store column 1 = name)
        text_renderer = Gtk.CellRendererText()
        text_col = Gtk.TreeViewColumn("Payloads", text_renderer)
        text_col.set_cell_data_func(text_renderer, self._payload_text_data_func)
        tree.append_column(text_col)

    def _configure_tree_selections(self) -> None:
        # Probes: single-select to prevent machine overload
        tree = self.builder.get_object("workspace_tree")
        if tree is not None:
            selection = tree.get_selection()
            if selection is not None:
                selection.set_mode(Gtk.SelectionMode.SINGLE)

        # Payloads: single-select for details display (checkboxes handle multi-select)
        tree = self.builder.get_object("widget_tree_view")
        if tree is not None:
            selection = tree.get_selection()
            if selection is not None:
                selection.set_mode(Gtk.SelectionMode.SINGLE)

    # ── Payload cell data functions ──────────────────────────────────

    def _payload_toggle_data_func(self, _column, renderer, model, tree_iter, _data=None):
        """Control checkbox state and sensitivity from store columns."""
        checked = model.get_value(tree_iter, 0)
        enabled = model.get_value(tree_iter, 3)
        renderer.set_property("active", checked)
        renderer.set_property("activatable", enabled)
        renderer.set_property("sensitive", enabled)

    def _payload_text_data_func(self, _column, renderer, model, tree_iter, _data=None):
        """Control text display and graying for disabled payloads."""
        name = model.get_value(tree_iter, 1)
        enabled = model.get_value(tree_iter, 3)
        renderer.set_property("text", name)
        if enabled:
            renderer.set_property("foreground-set", False)
        else:
            renderer.set_property("foreground", "#4a5568")
            renderer.set_property("foreground-set", True)

    # ── Filter functions ─────────────────────────────────────────────

    def _probe_filter_func(self, model, tree_iter, _data) -> bool:
        if not self._probe_search_text:
            return True
        name = (model.get_value(tree_iter, 0) or "").lower()
        if self._probe_search_text in name:
            return True
        child = model.iter_children(tree_iter)
        while child is not None:
            child_name = (model.get_value(child, 0) or "").lower()
            if self._probe_search_text in child_name:
                return True
            child = model.iter_next(child)
        return False

    def _payload_filter_func(self, model, tree_iter, _data) -> bool:
        if not self._payload_search_text:
            return True
        # Column 1 is name in the new schema (col 0 is checked bool)
        name = (model.get_value(tree_iter, 1) or "").lower()
        if self._payload_search_text in name:
            return True
        child = model.iter_children(tree_iter)
        while child is not None:
            child_name = (model.get_value(child, 1) or "").lower()
            if self._payload_search_text in child_name:
                return True
            child = model.iter_next(child)
        return False

    # ── Tree loading ─────────────────────────────────────────────────

    def _load_probe_tree(self) -> None:
        store = Gtk.TreeStore(str, str)  # name, id
        categories = self.probe_manager.get_categories()

        for category_name in sorted(categories.keys()):
            parent = store.append(None, [category_name, ""])
            for probe in sorted(categories[category_name], key=lambda p: p["name"]):
                probe_id = probe["id"]
                self._probe_index[probe_id] = probe
                store.append(parent, [probe["name"], probe_id])

        self._probe_filter = store.filter_new()
        self._probe_filter.set_visible_func(self._probe_filter_func)

        tree = self.builder.get_object("workspace_tree")
        if tree is not None:
            tree.set_model(self._probe_filter)
            tree.expand_all()

    def _load_payload_tree(self) -> None:
        # Columns: checked (bool), name (str), id (str), enabled (bool)
        store = Gtk.TreeStore(bool, str, str, bool)
        categories = self.payload_manager.get_categories()

        for category_name in sorted(categories.keys()):
            parent = store.append(None, [False, category_name, "", True])
            for payload in sorted(categories[category_name], key=lambda p: p["name"]):
                payload_id = payload["id"]
                payload_obj = self.payload_manager.get_payload(payload_id)
                self._payload_index[payload_id] = payload_obj
                store.append(parent, [False, payload["name"], payload_id, True])

        self._payload_store = store
        self._payload_filter = store.filter_new()
        self._payload_filter.set_visible_func(self._payload_filter_func)

        tree = self.builder.get_object("widget_tree_view")
        if tree is not None:
            tree.set_model(self._payload_filter)
            tree.expand_all()

    # ── Model combo ──────────────────────────────────────────────────

    def _setup_model_combo(self) -> None:
        """Populate the model dropdown from ProbeManager.VERIFIED_MODELS."""
        combo = self.builder.get_object("model_combo")
        if combo is None:
            return
        models = list(self.probe_manager.VERIFIED_MODELS)
        if not models:
            self.logger.error(
                "No verified models are configured; workload warnings will use defaults"
            )
            return
        for model_name in models:
            combo.append_text(model_name)
        combo.set_active(0)
        self._selected_model = models[0]

    def on_model_combo_changed(self, combo) -> None:
        def _action() -> None:
            active_text = combo.get_active_text()
            if active_text:
                self._selected_model = active_text
                self.logger.info("Model selected: %s", self._selected_model)
            self._refresh_selection_status()

        self._safe_ui_action("model selection", _action)

    # ── Selection helpers ────────────────────────────────────────────

    def _get_selected_probes(self) -> List[str]:
        """Get selected probe IDs (0 or 1 with single-select)."""
        tree = self.builder.get_object("workspace_tree")
        if tree is None:
            return []
        selection = tree.get_selection()
        if selection is None:
            return []
        model, paths = selection.get_selected_rows()
        if model is None:
            return []

        ids: List[str] = []
        for path in paths:
            tree_iter = model.get_iter(path)
            if tree_iter is None:
                continue
            item_id = model.get_value(tree_iter, 1)
            if item_id and item_id in self._probe_index:
                ids.append(item_id)
        return ids

    def _get_selected_payloads(self) -> List[str]:
        """Get checked payload IDs by walking the payload store."""
        store = self._payload_store
        if store is None:
            return []

        ids: List[str] = []
        parent_iter = store.get_iter_first()
        while parent_iter is not None:
            child_iter = store.iter_children(parent_iter)
            while child_iter is not None:
                checked = store.get_value(child_iter, 0)
                payload_id = store.get_value(child_iter, 2)
                if checked and payload_id and payload_id in self._payload_index:
                    ids.append(payload_id)
                child_iter = store.iter_next(child_iter)
            parent_iter = store.iter_next(parent_iter)
        return ids

    # ── Payload toggle handler ───────────────────────────────────────

    def _on_payload_toggled(self, _renderer, path_str) -> None:
        def _action() -> None:
            tree = self.builder.get_object("widget_tree_view")
            if tree is None:
                return
            filter_model = tree.get_model()
            if filter_model is None:
                return

            filter_path = Gtk.TreePath.new_from_string(path_str)
            filter_iter = filter_model.get_iter(filter_path)
            if filter_iter is None:
                return

            # Convert filter path to underlying store path
            store_path = filter_model.convert_path_to_child_path(filter_path)
            if store_path is None:
                return

            store = self._payload_store
            if store is None:
                return
            store_iter = store.get_iter(store_path)
            if store_iter is None:
                return

            # Block toggle if row is disabled
            enabled = store.get_value(store_iter, 3)
            if not enabled:
                return

            current = store.get_value(store_iter, 0)
            new_val = not current
            payload_id = store.get_value(store_iter, 2)

            if payload_id:
                # Leaf row: just flip it
                store.set_value(store_iter, 0, new_val)
            else:
                # Category row: toggle all enabled children
                store.set_value(store_iter, 0, new_val)
                child_iter = store.iter_children(store_iter)
                while child_iter is not None:
                    if store.get_value(child_iter, 3):  # only toggle enabled children
                        store.set_value(child_iter, 0, new_val)
                    child_iter = store.iter_next(child_iter)

            self._sync_category_check_state()
            self._refresh_selection_status()

        self._safe_ui_action("payload toggle", _action)

    def _sync_category_check_state(self) -> None:
        """Set each category row's checked state based on its children."""
        store = self._payload_store
        if store is None:
            return
        parent_iter = store.get_iter_first()
        while parent_iter is not None:
            all_checked = True
            any_child = False
            child_iter = store.iter_children(parent_iter)
            while child_iter is not None:
                any_child = True
                if store.get_value(child_iter, 3) and not store.get_value(child_iter, 0):
                    all_checked = False
                    break
                child_iter = store.iter_next(child_iter)
            store.set_value(parent_iter, 0, all_checked and any_child)
            parent_iter = store.iter_next(parent_iter)

    # ── Payload compatibility ────────────────────────────────────────

    def _get_selected_probe_category(self) -> Optional[str]:
        """Return the category of the single selected probe, or None."""
        probe_ids = self._get_selected_probes()
        if not probe_ids:
            return None
        probe = self._probe_index.get(probe_ids[0])
        if probe is None:
            return None
        return probe.get("category")

    def _update_payload_sensitivity(self) -> None:
        """Enable/disable payload rows based on selected probe's compatibility."""
        store = self._payload_store
        if store is None:
            return

        probe_cat = self._get_selected_probe_category()

        # No probe selected: everything enabled
        if probe_cat is None:
            compatible = None  # means all enabled
        else:
            mapping = PROBE_PAYLOAD_COMPATIBILITY.get(probe_cat)
            if mapping is not None:
                compatible = set(mapping) | set(ALWAYS_ENABLED_CATEGORIES)
            else:
                compatible = None  # unknown probe category: allow all

        parent_iter = store.get_iter_first()
        while parent_iter is not None:
            category_name = store.get_value(parent_iter, 1)
            cat_enabled = compatible is None or category_name in compatible

            # Update children
            child_iter = store.iter_children(parent_iter)
            while child_iter is not None:
                store.set_value(child_iter, 3, cat_enabled)
                # Uncheck disabled payloads
                if not cat_enabled and store.get_value(child_iter, 0):
                    store.set_value(child_iter, 0, False)
                child_iter = store.iter_next(child_iter)

            # Parent enabled if any child is enabled
            store.set_value(parent_iter, 3, cat_enabled)
            if not cat_enabled and store.get_value(parent_iter, 0):
                store.set_value(parent_iter, 0, False)

            parent_iter = store.iter_next(parent_iter)

        self._sync_category_check_state()

    # ── Workload warning ─────────────────────────────────────────────

    def _get_workload_threshold(self) -> int:
        """Return the payload warning threshold for the current model."""
        weight = MODEL_WEIGHT.get(self._selected_model, "medium")
        return PAYLOAD_WARN_THRESHOLDS.get(weight, 10)

    # ── Status ───────────────────────────────────────────────────────

    def _refresh_selection_status(self) -> None:
        if self._run_active:
            return
        probes_count = len(self._get_selected_probes())
        payload_count = len(self._get_selected_payloads())
        threshold = self._get_workload_threshold()

        if payload_count >= threshold:
            weight = MODEL_WEIGHT.get(self._selected_model, "medium")
            self._set_status(
                f"{payload_count} payload(s) on {self._selected_model} ({weight}) "
                f"-- heavy workload, may be slow"
            )
        else:
            self._set_status(
                f"Selected {probes_count} probe(s) and {payload_count} payload(s)"
            )

    # ── Detail panels ────────────────────────────────────────────────

    def _update_probe_details(self, probe: Optional[Dict]) -> None:
        general = self.builder.get_object("tab_general_content")
        packing = self.builder.get_object("tab_packing_content")
        common = self.builder.get_object("tab_common_content")
        signals = self.builder.get_object("tab_signals_content")

        if probe is None:
            if general is not None:
                general.set_text("Select a probe to inspect details.")
            if packing is not None:
                packing.set_text("Probe metadata will appear here.")
            if common is not None:
                common.set_text("Probe template preview will appear here.")
            if signals is not None:
                signals.set_text(
                    "Select a probe and payloads, then click Run to simulate."
                )
            return

        probe_name = probe.get("name", "Unknown")
        category = probe.get("category", "Unknown")
        description = probe.get("description", "")
        garak_probe = probe.get("garak_probe", "(none)")
        template = str(probe.get("template", ""))
        template_preview = template[:800] + "\n..." if len(template) > 800 else template

        if general is not None:
            general.set_text(
                f"Probe: {probe_name}\n"
                f"Category: {category}\n\n"
                f"Description:\n{description}"
            )

        if packing is not None:
            packing.set_text(
                f"Mapping: {garak_probe}\n"
                "Execution mode: local simulation only\n"
                "NVIDIA/CLI integration: disabled"
            )

        if common is not None:
            common.set_text(f"Template preview:\n\n{template_preview}")

        if signals is not None:
            signals.set_text(
                "Ready to run probe/payload matrix.\n"
                "Click Run to compose prompts locally."
            )

    def _update_payload_details(self, payload: Optional[Dict]) -> None:
        general = self.builder.get_object("tab_general_content")
        packing = self.builder.get_object("tab_packing_content")
        common = self.builder.get_object("tab_common_content")
        signals = self.builder.get_object("tab_signals_content")

        if payload is None:
            if general is not None:
                general.set_text("Select a payload to inspect details.")
            if packing is not None:
                packing.set_text("Payload metadata will appear here.")
            if common is not None:
                common.set_text("Payload text preview will appear here.")
            if signals is not None:
                signals.set_text(
                    "Select a probe and payloads, then click Run to simulate."
                )
            return

        payload_name = payload.get("name", "Unknown")
        category = payload.get("category", "Unknown")
        severity = payload.get("severity", "unknown")
        text = str(payload.get("text", ""))
        preview = text[:800] + "\n..." if len(text) > 800 else text
        source = payload.get("source")
        source_url = payload.get("source_url")
        technique = payload.get("technique")
        benchmark_family = payload.get("benchmark_family")
        benchmark_category = payload.get("benchmark_category")
        notes = payload.get("notes")

        if general is not None:
            general.set_text(
                f"Payload: {payload_name}\n"
                f"Category: {category}\n\n"
                f"Severity: {severity}"
            )

        if packing is not None:
            meta_lines = []
            if source:
                meta_lines.append(f"Source: {source}")
            if technique:
                meta_lines.append(f"Technique: {technique}")
            if benchmark_family or benchmark_category:
                fam = benchmark_family or "(none)"
                cat = benchmark_category or "(none)"
                meta_lines.append(f"Benchmark: {fam} / {cat}")
            if source_url:
                meta_lines.append(f"Source URL: {source_url}")
            if notes:
                meta_lines.append(f"Notes: {notes}")
            meta_text = "\n".join(meta_lines) if meta_lines else "Source: (none)"

            packing.set_text(
                f"Payload length: {len(text)} chars\n"
                f"Severity: {severity}\n"
                f"{meta_text}\n"
                "Execution mode: local simulation only"
            )

        if common is not None:
            common.set_text(f"Payload preview:\n\n{preview}")

        if signals is not None:
            signals.set_text(
                "Payload selected.\n"
                "Run combines selected probe x checked payloads without CLI."
            )

    # ── Progress / run controls ──────────────────────────────────────

    def _set_progress_idle(self) -> None:
        self._set_progress(0.0, "Idle")
        self._set_eta("ETA: --:--")
        cancel_button = self.builder.get_object("cancel_button")
        if cancel_button is not None:
            cancel_button.set_sensitive(False)

    def _set_run_controls(self, is_running: bool) -> None:
        for widget_id in (
            "workspace_tree", "widget_tree_view",
            "widget_search_entry", "probe_search_entry",
            "model_combo",
        ):
            widget = self.builder.get_object(widget_id)
            if widget is not None:
                widget.set_sensitive(not is_running)
        run_button = self.builder.get_object("tool_run")
        if run_button is not None:
            run_button.set_sensitive(not is_running)
        cancel_button = self.builder.get_object("cancel_button")
        if cancel_button is not None:
            cancel_button.set_sensitive(is_running)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        total = max(0, int(seconds))
        mins, secs = divmod(total, 60)
        return f"{mins:02d}:{secs:02d}"

    def _update_run_progress(self) -> None:
        if self._run_total <= 0:
            self._set_progress(0.0, "Idle")
            self._set_eta("ETA: --:--")
            return

        fraction = self._run_completed / self._run_total
        self._set_progress(fraction, f"{self._run_completed}/{self._run_total}")

        if self._run_completed <= 0 or self._run_completed >= self._run_total:
            self._set_eta("ETA: 00:00" if self._run_completed >= self._run_total else "ETA: --:--")
            return

        elapsed = time.monotonic() - self._run_started_at
        average = elapsed / self._run_completed
        remaining = average * (self._run_total - self._run_completed)
        self._set_eta(f"ETA: {self._format_duration(remaining)}")

    def _compose_prompt(self, probe: Dict, payload: Dict) -> str:
        template = str(probe.get("template", ""))
        payload_text = str(payload.get("text", ""))
        if "{payload}" in template:
            return template.replace("{payload}", payload_text)
        if template:
            return f"{template}\n\n--- Payload ---\n{payload_text}"
        return payload_text

    def _render_run_preview(self, probe: Dict, payload: Dict, composed_prompt: str) -> None:
        general = self.builder.get_object("tab_general_content")
        packing = self.builder.get_object("tab_packing_content")
        common = self.builder.get_object("tab_common_content")
        signals = self.builder.get_object("tab_signals_content")

        if general is not None:
            general.set_text(
                f"Run item {self._run_completed}/{self._run_total}\n"
                f"Model: {self._selected_model}\n"
                f"Probe: {probe.get('name', 'Unknown')}\n"
                f"Payload: {payload.get('name', 'Unknown')}\n"
                f"Payload severity: {payload.get('severity', 'unknown')}"
            )

        if packing is not None:
            selected_payloads = len(self._get_selected_payloads())
            packing.set_text(
                f"Matrix: 1 probe x {selected_payloads} payload(s)\n"
                f"Combinations: {self._run_total}\n"
                f"Model: {self._selected_model}\n"
                "Runtime: local simulation only"
            )

        if common is not None:
            preview = composed_prompt[:1800] + "\n..." if len(composed_prompt) > 1800 else composed_prompt
            common.set_text(f"Composed prompt preview:\n\n{preview}")

        if signals is not None:
            signals.set_text(
                "Simulation step complete.\n"
                "No external CLI/API commands were executed."
            )

    # ── Run lifecycle ────────────────────────────────────────────────

    def _start_run(self) -> None:
        if self._run_active:
            self._set_status("Run already in progress.")
            return

        selected_probes = self._get_selected_probes()
        selected_payloads = self._get_selected_payloads()

        if not selected_probes:
            self._set_status("Select a probe before running.")
            return
        if not selected_payloads:
            self._set_status("Check at least one payload before running.")
            return

        self._run_queue = deque(
            (probe_id, payload_id)
            for probe_id in selected_probes
            for payload_id in selected_payloads
        )
        self._run_total = len(self._run_queue)
        self._run_completed = 0
        self._run_started_at = time.monotonic()
        self._cancel_requested = False
        self._run_active = True

        self._set_run_controls(True)
        self._update_run_progress()

        threshold = self._get_workload_threshold()
        if len(selected_payloads) >= threshold:
            self._set_status(
                f"Running {self._run_total} combinations on {self._selected_model} "
                f"(heavy workload)..."
            )
        else:
            self._set_status(
                f"Running {self._run_total} combinations on {self._selected_model}..."
            )

        self._run_source_id = GLib.timeout_add(35, self._on_run_tick)

    def _finish_run(self, canceled: bool, remove_source: bool = True) -> None:
        if remove_source and self._run_source_id is not None:
            GLib.source_remove(self._run_source_id)
            self._run_source_id = None
        elif not remove_source:
            self._run_source_id = None

        self._run_active = False
        self._run_queue.clear()
        self._set_run_controls(False)

        if canceled:
            self._set_status(
                f"Canceled at {self._run_completed}/{self._run_total} combinations."
            )
            fraction = (
                self._run_completed / self._run_total if self._run_total > 0 else 0.0
            )
            self._set_progress(
                fraction,
                f"Canceled {self._run_completed}/{self._run_total}",
            )
            self._set_eta("ETA: --:--")
            return

        self._run_completed = self._run_total
        self._update_run_progress()
        self._set_status(f"Completed {self._run_total} combinations.")

    def _on_run_tick(self) -> bool:
        try:
            if not self._run_active:
                return False

            if self._cancel_requested:
                self._finish_run(canceled=True, remove_source=False)
                return False

            if not self._run_queue:
                self._finish_run(canceled=False, remove_source=False)
                return False

            probe_id, payload_id = self._run_queue.popleft()
            probe = self._probe_index.get(probe_id) or self.probe_manager.get_probe(
                probe_id
            )
            payload = self._payload_index.get(
                payload_id
            ) or self.payload_manager.get_payload(payload_id)
            if not probe or not payload:
                raise RuntimeError(
                    f"Missing run item data for probe={probe_id}, payload={payload_id}"
                )

            composed = self._compose_prompt(probe, payload)
            self._run_completed += 1
            self._render_run_preview(probe, payload, composed)
            self._update_run_progress()
            self._set_status(
                f"Running... {self._run_completed}/{self._run_total} completed"
            )
            return True
        except Exception:
            self.logger.exception("Run tick failed; stopping run safely")
            self._finish_run(canceled=True, remove_source=False)
            self._set_status(
                "Run failed due to an internal error. Check logs/"
            )
            return False

    # ── Signal handlers (connected via Glade) ────────────────────────

    def on_main_window_destroy(self, *_args) -> None:
        if self._run_source_id is not None:
            GLib.source_remove(self._run_source_id)
            self._run_source_id = None
        Gtk.main_quit()

    def on_run_clicked(self, _button) -> None:
        self._safe_ui_action("run click", self._start_run)

    def on_cancel_clicked(self, _button) -> None:
        def _action() -> None:
            if not self._run_active:
                self._set_status("No run in progress to cancel.")
                return
            self._cancel_requested = True
            self._finish_run(canceled=True)

        self._safe_ui_action("cancel click", _action)

    def on_workspace_tree_selection_changed(self, selection) -> None:
        def _action() -> None:
            probe_ids = self._get_selected_probes()
            if not probe_ids:
                self._update_probe_details(None)
                self._update_payload_sensitivity()
                self._refresh_selection_status()
                return

            selected_probe = self._probe_index.get(
                probe_ids[0], self.probe_manager.get_probe(probe_ids[0])
            )
            self._update_probe_details(selected_probe)
            self._update_payload_sensitivity()
            self._refresh_selection_status()

        self._safe_ui_action("probe selection", _action)

    def on_payload_tree_selection_changed(self, _selection) -> None:
        """Show details for the clicked payload row (separate from checkbox)."""
        def _action() -> None:
            tree = self.builder.get_object("widget_tree_view")
            if tree is None:
                return
            selection = tree.get_selection()
            if selection is None:
                return
            model, paths = selection.get_selected_rows()
            if model is None or not paths:
                self._update_payload_details(None)
                return

            tree_iter = model.get_iter(paths[0])
            if tree_iter is None:
                self._update_payload_details(None)
                return

            payload_id = model.get_value(tree_iter, 2)
            if payload_id and payload_id in self._payload_index:
                self._update_payload_details(self._payload_index[payload_id])
            else:
                self._update_payload_details(None)

        self._safe_ui_action("payload selection", _action)

    def on_probe_search_changed(self, entry) -> None:
        def _action() -> None:
            self._probe_search_text = (entry.get_text() or "").lower()
            self._probe_filter.refilter()
            tree = self.builder.get_object("workspace_tree")
            if tree is not None:
                tree.expand_all()

        self._safe_ui_action("probe search", _action)

    def on_payload_search_changed(self, entry) -> None:
        def _action() -> None:
            self._payload_search_text = (entry.get_text() or "").lower()
            self._payload_filter.refilter()
            tree = self.builder.get_object("widget_tree_view")
            if tree is not None:
                tree.expand_all()

        self._safe_ui_action("payload search", _action)

    def on_property_notebook_switch_page(self, _notebook, _page, page_num: int) -> None:
        self._safe_ui_action(
            "notebook switch",
            lambda: self._set_status(f"Details tab index: {page_num}"),
        )
