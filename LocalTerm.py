#
# Gramps - a GTK+/GNOME based genealogy program
#
# LocalTerm Gramplet – Localized Gramps Glossary Terminology
#
# ----------------------------------------------------------------------
# Copyright (C) 2025 Kaj Mikkelsen <kmi@vgdata.dk>
# Copyright (C) 2026 Codex / ChatGPT
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# ----------------------------------------------------------------------
# Evolution / Change log
#
# 20251008 Initial implementation
# added strip to the dequote function
# added dictionaries
# filling gui from dictionary instead of from file
# 20251009
# added functionality for two languages
# cleaned up the setup
# 20251014
# Fixed issue with error when calling the URL
# changed header names
# 20251022 Weblate CSV support
# Added more test files (Thanks Brian McCullough)
# Changes filenames to csv
# verified that the file glob ignores case
# added the setup option of hiding the anchor column
# added the function of changing the anchor visibility in runtime
# 20251023
# if anchor starts with https:// the anchor becomes the URL otherwise
#   URL is Combined from the baseurl in setup and the anchor
# added search functionality
# added search language option
# 20251024
# added function clean_translatable to remove _() from the translatable term
# removed active change routine, this has nothing to do with the active person
# 20251105
# changed language selection to drop down boxes
# added function to set the file array based on the selected languages
# changed loading of files to use the file array
# 20251106
# Made column language2 invisble if only on language is selected
# 20260110
# made more fault tolerant: fail 5 line testings report and abort
# adapt to 8 column CSV downloaded from WebLate GrampsGlossary component
#  original 3 columns: term, translatable, anchor
#  location,source,target,id,fuzzy,context,translator_comments,developer_comments
# 2026-01-18
#   - Filename-based language selection (no indices)
#   - Robust CSV parsing via Python csv module
#   - Correct anchor source (developer_comments)
#   - Config schema versioning
#   - Flush-to-defaults on schema mismatch
#   - Removed plugin-version introspection (unstable API)
# 2026-01-20
# - Add context menu with clipboard support and external opening of Weblate CSV.
# - Improve TreeView presentation and consistency (anchor column last; headers and rows aligned).
# - Fix GTK lifecycle and context-menu handling (selection, popup parenting, warning cleanup).
# - Add support for language-level CSV metadata (detect language context; use endonym headers; graceful fallback).
# - Lay groundwork for expanded metadata usage (extensible keys; future tooltip support).
# - Fix CSV load crash caused by uninitialized context variable.
# 2026-01-24
#
# 2026-01-25
# - Detect duplicate 'source' keys within Language-1 CSV rows (not between languages).
# - Preserve duplicate Language-1 rows by appending internal row index keys.
# - Mark duplicate Language-1 rows without collapsing data.
# - Add optional "Track Changes" to highlight L1/L2 row value mismatches.
# - Add configuration option for enabling/disabling Track Changes.
# - Bump config schema version to reflect new option.
# - Refactor config handling to named options (remove index-based access).
# - Stabilize Configure dialog after schema flushes and option reordering.
#
# ----------------------------------------------------------------------

import os
import glob
import csv
import logging
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio

from gramps.gen.plug import Gramplet
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.config import config
from gramps.gui.display import display_url
from gramps.gui.dialog import ErrorDialog
from gramps.gen.plug.menu import (
    BooleanOption,
    StringOption,
    NumberOption,
    ColorOption,
    EnumeratedListOption,
)
from gramps.gen.lib import Note
from gramps.gui.editors import EditNote

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------

LOG = logging.getLogger("LocalTerm")
LOG.setLevel(logging.INFO)

# ----------------------------------------------------------------------
# Translation
# ----------------------------------------------------------------------

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

# ----------------------------------------------------------------------
# Model column indices
# Anchor MUST be the last data column
# ----------------------------------------------------------------------

COL_TERM        = 0
COL_TARGET      = 1
COL_LANG2       = 2
COL_TR_COM_TGT  = 3   # NEW for 1.0.8
COL_TR_COM_L2   = 4   # NEW for 1.0.8
COL_ANCHOR      = 5
COL_FG          = 6
COL_BG          = 7


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

# TODO:
# CONFIG_ID is currently used both for config identity and diagnostics.
# This is intentional for now. A later refactor may separate persistent
# identity from schema/version labeling.
CONFIG_ID = "LocalTerm"

CONFIG_SCHEMA_VERSION = "0.2.5"

PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

# IMPORTANT: no ".ini" — Gramps adds it
_config_file = os.path.join(PLUGIN_DIR, CONFIG_ID)

config = config.register_manager(_config_file)

# schema metadata
config.register("localterm.config_id", CONFIG_ID)
# IMPORTANT:
# config_schema MUST NOT default to the current version,
# otherwise Gramps will comment it out and schema mismatch
# detection will never trigger.
# config.register("localterm.config_schema", CONFIG_SCHEMA_VERSION)
config.register("localterm.config_schema", "")

# options
config.register("localterm.show_anchor", False)
config.register("localterm.track_changes", True)
config.register("localterm.url_bas", "https://gramps-project.org/wiki/index.php/")
config.register("localterm.search_lang", 1)
config.register("localterm.fg_sel_col", "#000000")
config.register("localterm.bg_sel_col", "#ffffff")
config.register("localterm.lang1_file", "")
config.register("localterm.lang2_file", "")

# ----------------------------------------------------------------------
# Gramplet
# ----------------------------------------------------------------------

def _norm(value):
    """Normalize CSV fields (strip + lowercase)."""
    return value.strip().lower() if value else ""


def is_language_metadata(context, source, key):
    """
    True if this row is language-level metadata with the given key.
    Case- and whitespace-insensitive.
    """
    return _norm(context) == "language" and _norm(source) == key

class LocalTerm(Gramplet):
    """
    Localized index to Gramps glossary terminology.

    NOTE:
    Preferences are NOT migrated.
    Any config schema mismatch flushes settings to defaults.
    """

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _validate_or_flush_config(self):
        """
        Validate config identity and schema.

        LocalTerm configs are NOT migrated.
        Any mismatch results in a full reset to defaults.
        """
        cfg_id = config.get("localterm.config_id")
        cfg_schema = config.get("localterm.config_schema")

        if cfg_id != CONFIG_ID or cfg_schema != CONFIG_SCHEMA_VERSION:
            LOG.info(
                "LocalTerm config mismatch (id=%r schema=%r); flushing",
                cfg_id,
                cfg_schema,
            )
            config.reset()
            config.set("localterm.config_id", CONFIG_ID)
            config.set("localterm.config_schema", CONFIG_SCHEMA_VERSION)
            config.save()

    def _load_files(self):
        pattern = os.path.join(
            os.path.dirname(__file__),
            "gramps-project-glossary",
            "gramps-project-glossary-*.csv",
        )
        self.__files = sorted(glob.glob(pattern))

    def _index_for_file(self, filename, fallback=0):
        for i, f in enumerate(self.__files):
            if os.path.basename(f) == filename:
                return i
        return fallback

    def clean_translatable(self, s):
        s = s.strip()
        if s.startswith("_(") and s.endswith(")"):
            return s[2:-1].strip()
        return s

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self):
        config.load()
        self._validate_or_flush_config()
        self._load_files()

        self.lang1_txt = {}
        self.lang2_txt = {}
        self.lang1_trcom = {}
        self.lang2_trcom = {}
        self.lang1_loc = {}
        self.lang2_loc = {}

        self.lang1_base = {}            # <<< CHANGED: row_key → base_source
        self.source_row_index = {}      # <<< CHANGED: per-file row counter
        self.duplicate_rows = set()     # <<< CHANGED: row_keys that are duplicates

        self.lang1_endonym = None
        self.lang2_endonym = None

        self.dup_fg = "#CC5500"     # NEW: Weblate-style dark orange fg for dups (on light bg)
        self.dup_bg = "#FFF2CC"  # NEW: Weblate-style pale yellow bg for dups
        self.change_fg = self.dup_fg          # same foreground
        self.change_bg = "#E6F4EA"            # pale green


        self.gui.WIDGET = self.build_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.gui.WIDGET)
        self.gui.WIDGET.show()

    def on_load(self):
        self.__show_anchor = config.get("localterm.show_anchor")
        self.__track_changes = config.get("localterm.track_changes")
        self.__search_lang = config.get("localterm.search_lang")
        self.__url_bas = config.get("localterm.url_bas")
        self.__fg_sel = config.get("localterm.fg_sel_col")
        self.__bg_sel = config.get("localterm.bg_sel_col")

        self.__lang1_file = config.get("localterm.lang1_file")
        self.__lang2_file = config.get("localterm.lang2_file")

        self._load_files()

        self.__lang1 = self._index_for_file(self.__lang1_file, 0)
        self.__lang2 = self._index_for_file(self.__lang2_file, self.__lang1)

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    def build_options(self):
        self._load_files()
        self.opts = []

        self.opt_url = StringOption(
            _("URL base for glossary anchors"), self.__url_bas
        )
        self.opt_show_anchor = BooleanOption(
            _("Show anchor column"), self.__show_anchor
        )
        self.opt_track_changes = BooleanOption(
            _("Track Changes"), self.__track_changes
        )
        self.opt_search_lang = NumberOption(
            _("Search language"), self.__search_lang, 1, 2, 1
        )
        self.opt_fg = ColorOption(
            _("Foreground color"), self.__fg_sel
        )
        self.opt_bg = ColorOption(
            _("Background color"), self.__bg_sel
        )

        self.opts = [
            self.opt_url,
            self.opt_show_anchor,
            self.opt_track_changes,   # ← exactly where you wanted it
            self.opt_search_lang,
            self.opt_fg,
            self.opt_bg,
        ]

        self.opt_lang1 = EnumeratedListOption(_("Language 1"), self.__lang1)
        for i, f in enumerate(self.__files):
            self.opt_lang1.add_item(i, os.path.basename(f))
        self.opts.append(self.opt_lang1)

        self.opt_lang2 = EnumeratedListOption(_("Language 2"), self.__lang2)
        for i, f in enumerate(self.__files):
            self.opt_lang2.add_item(i, os.path.basename(f))
        self.opts.append(self.opt_lang2)

        for opt in self.opts:
            self.add_option(opt)

    def save_options(self):
        self.__url_bas = self.opt_url.get_value()
        self.__show_anchor = self.opt_show_anchor.get_value()
        self.__track_changes = self.opt_track_changes.get_value()
        self.__search_lang = self.opt_search_lang.get_value()
        self.__fg_sel = self.opt_fg.get_value()
        self.__bg_sel = self.opt_bg.get_value()

        self.__lang1 = self.opt_lang1.get_value()
        self.__lang2 = self.opt_lang2.get_value()

        config.set("localterm.show_anchor", self.__show_anchor)
        config.set("localterm.url_bas", self.__url_bas)
        config.set("localterm.search_lang", self.__search_lang)
        config.set("localterm.fg_sel_col", self.__fg_sel)
        config.set("localterm.bg_sel_col", self.__bg_sel)

        if self.__files:
            config.set(
                "localterm.lang1_file",
                os.path.basename(self.__files[self.__lang1]),
            )
            config.set(
                "localterm.lang2_file",
                os.path.basename(self.__files[self.__lang2]),
            )

        config.set("localterm.config_id", CONFIG_ID)
        config.set("localterm.config_schema", CONFIG_SCHEMA_VERSION)
        config.save()

    def save_update_options(self, _obj):
        self.save_options()
        self.update()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def set_fl_ar(self):
        self.__fl_ar = []
        if not self.__files:
            return

        self.__fl_ar.append(self.__files[self.__lang1])
        if self.__lang2 != self.__lang1:
            self.__fl_ar.append(self.__files[self.__lang2])

    def load_file(self, flnm):
        if self.filenbr == 0:
            self.lang1_txt.clear()
            self.lang1_trcom.clear()
            self.lang1_loc.clear()
            self.lang1_base.clear()      # <<< CHANGED
            self.source_row_index.clear()# <<< CHANGED
            self.duplicate_rows.clear()  # <<< CHANGED

        with open(flnm, encoding="utf-8", newline="") as csvfile:
            reader = csv.reader(csvfile)

            for lineno, row in enumerate(reader, start=1):
                if lineno == 1 or len(row) < 8:
                    continue

                source = self.clean_translatable(row[1])
                target = row[2].strip()
                context = row[5].strip()
                translator_comments = row[6].strip()
                anchor = row[7].strip()

                # Language-level metadata (endonym)
                if is_language_metadata(context, source, "endonym"):
                    if self.filenbr == 0:
                        self.lang1_endonym = target
                    else:
                        self.lang2_endonym = target
                    continue

                # ------------------------------------------------------
                # Language 1: preserve rows, mark duplicates
                # ------------------------------------------------------
                if self.filenbr == 0:
                    idx = self.source_row_index.get(source, 0) + 1
                    self.source_row_index[source] = idx

                    if idx == 1:
                        row_key = source
                    else:
                        row_key = f"{source}#{idx}"
                        self.duplicate_rows.add(row_key)   # <<< CHANGED

                    self.lang1_txt[row_key] = target
                    self.lang1_trcom[row_key] = translator_comments
                    self.lang1_loc[row_key] = anchor
                    self.lang1_base[row_key] = source

                # ------------------------------------------------------
                # Language 2: collapsed overlay
                # ------------------------------------------------------
                else:
                    self.lang2_txt[source] = target
                    self.lang2_trcom[source] = translator_comments
                    self.lang2_loc[source] = anchor

    # ------------------------------------------------------------------
    # Main / UI
    # ------------------------------------------------------------------

    def main(self):
        self.model.clear()
        self.set_fl_ar()

        self.gui.WIDGET.get_column(2).set_visible(self.__lang1 != self.__lang2)
        self.gui.WIDGET.get_column(3).set_visible(self.__show_anchor)
        self.gui.WIDGET.set_search_column(
            3 if self.__search_lang == 2 else 1
        )

        self.filenbr = 0
        for fl in self.__fl_ar:
            if os.path.isfile(fl):
                self.load_file(fl)
            self.filenbr += 1

        # --------------------------------------------------------------
        # Populate model row-by-row (no consolidation)
        # --------------------------------------------------------------
        for row_key, value in self.lang1_txt.items():
            base_source = self.lang1_base[row_key]

            is_dup = row_key in self.duplicate_rows

            base_source = self.lang1_base[row_key]
            l1_value = value or ""
            l2_value = self.lang2_txt.get(base_source, "") or ""

            is_changed = (
                self.__track_changes
                and l2_value
                and l1_value != l2_value
            )

            if is_dup:
                fg = self.dup_fg
                bg = self.dup_bg
            elif is_changed:
                fg = self.change_fg
                bg = self.change_bg
            else:
                fg = self.__fg_sel
                bg = self.__bg_sel

            self.model.append([
                base_source,                         # COL_TERM
                value,                               # COL_TARGET
                self.lang2_txt.get(base_source, ""), # COL_LANG2
                self.lang1_trcom.get(row_key, ""),   # COL_TR_COM_TGT
                self.lang2_trcom.get(base_source, ""),# COL_TR_COM_L2
                self.lang1_loc.get(row_key, ""),     # COL_ANCHOR
                fg,
                bg,
            ])

        # Apply endonyms to headers
        columns = self.gui.WIDGET.get_columns()

        columns[1].set_title(self.lang1_endonym or _("Target"))
        columns[2].set_title(self.lang2_endonym or _("Language 2"))



    def act(self, _tree_view, path, _column):
        tree_iter = self.model.get_iter(path)
        link = (self.model.get_value(tree_iter, COL_ANCHOR) or "").strip()

        if not link:
            return

        if link.startswith("https://"):
            url = link
        else:
            # Ensure exactly one slash between base and path
            base = self.__url_bas
            if not base.endswith("/"):
                base += "/"
            url = base + link.lstrip("/")

        display_url(url)

    def build_gui(self):
        self.model = Gtk.ListStore(
            str,  # term
            str,  # target
            str,  # lang2
            str,  # translator_comments (target)
            str,  # translator_comments (lang2)
            str,  # anchor
            str,  # fg
            str,  # bg
        )
        view = Gtk.TreeView(self.model)
        columns = view.get_columns()
        view.connect("row-activated", self.act)

        # Save reference for use from handlers
        self.treeview = view

        # Create popup menu for rows
        self.row_menu = Gtk.Menu()

        mi_note = Gtk.MenuItem(label=_("Create Note from row"))
        mi_note.connect("activate", self.create_note_from_selected_row)
        self.row_menu.append(mi_note)

        mi_copy = Gtk.MenuItem(label=_("Copy row to OS Clipboard"))
        mi_copy.connect("activate", self.copy_selected_row)
        self.row_menu.append(mi_copy)

        mi_open_csv = Gtk.MenuItem(label=_("Edit source CSV file"))
        mi_open_csv.connect("activate", self.open_source_csv)
        self.row_menu.append(mi_open_csv)

        self.row_menu.show_all()

        # Connect right-click handler
        view.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        view.connect("button-press-event", self.on_tree_button_press)

        renderer = Gtk.CellRendererText()

        view.append_column(
            Gtk.TreeViewColumn(_("English Term"), renderer, text=COL_TERM, foreground=COL_FG, background=COL_BG)
        )
        view.append_column(
            Gtk.TreeViewColumn(_("Target"), renderer, text=COL_TARGET, foreground=COL_FG, background=COL_BG)
        )
        view.append_column(
            Gtk.TreeViewColumn(_("Language 2"), renderer, text=COL_LANG2, foreground=COL_FG, background=COL_BG)
        )
        view.append_column(
            Gtk.TreeViewColumn(_("Anchor"), renderer, text=COL_ANCHOR, foreground=COL_FG, background=COL_BG)
        )

        view.set_search_column(1)
        self.model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.set_tooltip(_("Double click row to open glossary entry"))
        return view

    def on_tree_button_press(self, treeview, event):
        """
        Handle button-press-event to show a context menu on right-click for a row.
        Wayland-safe AND Gramps-safe.
        """
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            result = treeview.get_path_at_pos(int(event.x), int(event.y))
            if result is None:
                return False

            path, column, cell_x, cell_y = result

            # remember column for context-menu actions
            self._popup_column = column

            # Select the clicked row
            selection = treeview.get_selection()
            selection.select_path(path)

            # Attach menu ONLY if we have a real Gtk.Window
            toplevel = treeview.get_toplevel()
            if isinstance(toplevel, Gtk.Window) and self.row_menu.get_attach_widget() is None:
                self.row_menu.attach_to_widget(toplevel, None)

            # Popup menu (Wayland-safe)
            if hasattr(self.row_menu, "popup_at_pointer"):
                self.row_menu.popup_at_pointer(event)
            else:
                self.row_menu.popup(
                    None, None, None, None,
                    event.button, event.time
                )

            return True

        return False

    def create_note_from_selected_row(self, menu_item):
        """
        Create a new Gramps Note from the selected row.
        Fields are labeled and separated by TWO line breaks
        Anchor is expanded to a full URL and always last.
        """
        treeview = getattr(self, "treeview", None)
        if treeview is None:
            return

        selection = treeview.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            return

        parts = []

        def first_letter_anchor(url):
            """
            Reduce a glossary anchor URL to its alphabetical section.
            Example: ...#attribute -> ...#a
            """
            if "#" not in url:
                return ""
            base, frag = url.split("#", 1)
            return f"{base}#{frag[:1].upper()}" if frag else ""

        def add_block(header, value, comment=None):
            if not value:
                return
            block = f"{header}:\n{value}"
            if comment:
                block += f"\n{comment}"
            parts.append(block)

        add_block(
            _("English Term"),
            model.get_value(tree_iter, COL_TERM)
        )

        add_block(
            self.treeview.get_column(1).get_title(),
            model.get_value(tree_iter, COL_TARGET),
            model.get_value(tree_iter, COL_TR_COM_TGT),
        )

        add_block(
            self.treeview.get_column(2).get_title(),
            model.get_value(tree_iter, COL_LANG2),
            model.get_value(tree_iter, COL_TR_COM_L2),
        )

        # Compose anchor URL (same logic as act() / clipboard)

        raw_anchor = (model.get_value(tree_iter, COL_ANCHOR) or "").strip()
        if raw_anchor:
            if raw_anchor.startswith(("https://", "http://")):
                anchor_url = raw_anchor
            else:
                base = self.__url_bas
                if not base.endswith("/"):
                    base += "/"
                anchor_url = base + raw_anchor.lstrip("/")

            # Full anchor
            add_block(_("Anchor"), anchor_url)

            # Alphabetical section anchor (fallback when entry does not exist)
            section_anchor = first_letter_anchor(anchor_url)
            if section_anchor:
                parts.append("")
                parts.append(_("Glossary section:"))
                parts.append(section_anchor)

            # MediaWiki scratchpad

            parts.append("")
            parts.append(_("MediaWiki seed:"))

            # Extract bare MediaWiki anchor fragment (text after '#')
            raw_anchor = (model.get_value(tree_iter, COL_ANCHOR) or "").strip()
            term_id = ""
            if "#" in raw_anchor:
                term_id = raw_anchor.split("#", 1)[1]

            lang1_term = (model.get_value(tree_iter, COL_TARGET) or "").strip()
            lang1_desc = (model.get_value(tree_iter, COL_TR_COM_TGT) or "").strip()

            parts.append(
                f";<span id=\"english anchor\"/>"
                f"<span id=\"{term_id}\"/>"
                f"{lang1_term}: {lang1_desc}"
            )

        note_text = "\n\n".join(parts)

        # Create and open Note editor
        note = Note()
        note.set(note_text)

        EditNote(self.gui.dbstate, self.gui.uistate, [], note)

    def copy_selected_row(self, menu_item):
        """
        Copy the currently selected row's visible columns to the clipboard.
        Columns copied: 0 (English Term), 1 (Target), 2 (Anchor -> fully composed URL), 3 (Language 2)
        They will be joined by tabs for easy pasting into editors/spreadsheets.
        """
        treeview = getattr(self, "treeview", None)
        if treeview is None:
            return

        selection = treeview.get_selection()
        model, tree_iter = selection.get_selected()
        if tree_iter is None:
            return

        cols = [
            model.get_value(tree_iter, COL_TERM)   or "",
            model.get_value(tree_iter, COL_TARGET) or "",
            model.get_value(tree_iter, COL_LANG2)  or "",
        ]

        # Anchor (column 2) must be composed into full URL like act()
        raw_anchor = (model.get_value(tree_iter, COL_ANCHOR) or "").strip()

        if raw_anchor:
            if raw_anchor.startswith(("https://", "http://")):
                anchor_url = raw_anchor
            else:
                base = self.__url_bas
                if not base.endswith("/"):
                    base += "/"
                anchor_url = base + raw_anchor.lstrip("/")
        else:
            anchor_url = ""

        cols.append(anchor_url)   # Anchor ALWAYS last

        text = "\t".join(cols)

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        clipboard.store()

    def open_source_csv(self, menu_item):
        """
        Open the CSV file that is used to populate the Target column.
        The Target column corresponds to the language index self.__lang1.
        """
        # Prefer internal file list attributes used elsewhere in the gramplet
        files = getattr(self, "_LocalTerm__files", None)
        if not files:
            files = getattr(self, "_LocalTerm__fl_ar", None)
        if not files:
            files = getattr(self, "__files", None)

        if not files:
            LOG.error("No glossary CSV files found to open.")
            return

        # Determine index for the clicked column

        column = getattr(self, "_popup_column", None)

        if column:
            col_index = self.treeview.get_columns().index(column)

            if col_index == COL_LANG2:
                idx = self.__lang2
            else:
                idx = self.__lang1
        else:
            idx = self.__lang1

        try:
            csv_path = files[idx]
        except Exception:
            LOG.exception("Failed to determine CSV for Target column")
            return

        file_uri = "file://" + os.path.abspath(csv_path)

        # Try to open with the platform default application via Gio
        try:
            Gio.app_info_launch_default_for_uri(file_uri, None)
        except Exception:
            LOG.exception("Gio failed to open %s; falling back to display_url", file_uri)
            try:
                display_url(file_uri)
            except Exception:
                LOG.exception("Failed to open CSV %s", csv_path)
