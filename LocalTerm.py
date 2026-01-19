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
#   - Config schema versioning (alpha)
#   - Flush-to-defaults on schema mismatch
#   - Removed plugin-version introspection (unstable API)
#
# ----------------------------------------------------------------------

import os
import glob
import csv
import logging
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from gramps.gen.plug import Gramplet
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.config import config as configman
from gramps.gui.display import display_url
from gramps.gui.dialog import ErrorDialog
from gramps.gen.plug.menu import (
    BooleanOption,
    StringOption,
    NumberOption,
    ColorOption,
    EnumeratedListOption,
)

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
# Config schema (explicit, alpha)
# ----------------------------------------------------------------------

CONFIG_ID = "LocalTerm"
CONFIG_SCHEMA_VERSION = "0.0.1"

_config_file = os.path.join(
    os.path.dirname(__file__),
    "gramps-project-glossary",
    "LocalTerm",
)

config = configman.register_manager(_config_file)

config.register("myopt.config_id", "")
config.register("myopt.config_schema", "")

config.register("myopt.show_anchor", False)
config.register(
    "myopt.url_bas",
    "https://gramps-project.org/wiki/index.php/",
)
config.register("myopt.search_lang", 1)
config.register("myopt.fg_sel_col", "#000000")
config.register("myopt.bg_sel_col", "#ffffff")

# filename-based language selection
config.register("myopt.lang1_file", "")
config.register("myopt.lang2_file", "")

# ----------------------------------------------------------------------
# Gramplet
# ----------------------------------------------------------------------


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
        cfg_id = config.get("myopt.config_id")
        cfg_schema = config.get("myopt.config_schema")

        if cfg_id != CONFIG_ID or cfg_schema != CONFIG_SCHEMA_VERSION:
            LOG.info(
                "LocalTerm config mismatch (id=%r schema=%r); flushing",
                cfg_id,
                cfg_schema,
            )
            config.reset()
            config.set("myopt.config_id", CONFIG_ID)
            config.set("myopt.config_schema", CONFIG_SCHEMA_VERSION)
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

        self.gui.WIDGET = self.build_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.gui.WIDGET)
        self.gui.WIDGET.show()

        self.lang1_txt = {}
        self.lang2_txt = {}
        self.lang1_loc = {}
        self.lang2_loc = {}

    def on_load(self):
        self.__show_anchor = config.get("myopt.show_anchor")
        self.__search_lang = config.get("myopt.search_lang")
        self.__url_bas = config.get("myopt.url_bas")
        self.__fg_sel = config.get("myopt.fg_sel_col")
        self.__bg_sel = config.get("myopt.bg_sel_col")

        self.__lang1_file = config.get("myopt.lang1_file")
        self.__lang2_file = config.get("myopt.lang2_file")

        self._load_files()

        self.__lang1 = self._index_for_file(self.__lang1_file, 0)
        self.__lang2 = self._index_for_file(self.__lang2_file, self.__lang1)

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------

    def build_options(self):
        self._load_files()
        self.opts = []

        self.opts.append(
            StringOption(_("URL base for glossary anchors"), self.__url_bas)
        )
        self.opts.append(BooleanOption(_("Show anchor column"), self.__show_anchor))
        self.opts.append(
            NumberOption(_("Search language"), self.__search_lang, 1, 2, 1)
        )
        self.opts.append(ColorOption(_("Foreground color"), self.__fg_sel))
        self.opts.append(ColorOption(_("Background color"), self.__bg_sel))

        opt = EnumeratedListOption(_("Language 1"), self.__lang1)
        for i, f in enumerate(self.__files):
            opt.add_item(i, os.path.basename(f))
        self.opts.append(opt)

        opt = EnumeratedListOption(_("Language 2"), self.__lang2)
        for i, f in enumerate(self.__files):
            opt.add_item(i, os.path.basename(f))
        self.opts.append(opt)

        for opt in self.opts:
            self.add_option(opt)

    def save_options(self):
        self.__url_bas = self.opts[0].get_value()
        self.__show_anchor = self.opts[1].get_value()
        self.__search_lang = self.opts[2].get_value()
        self.__fg_sel = self.opts[3].get_value()
        self.__bg_sel = self.opts[4].get_value()
        self.__lang1 = self.opts[5].get_value()
        self.__lang2 = self.opts[6].get_value()

        config.set("myopt.show_anchor", self.__show_anchor)
        config.set("myopt.url_bas", self.__url_bas)
        config.set("myopt.search_lang", self.__search_lang)
        config.set("myopt.fg_sel_col", self.__fg_sel)
        config.set("myopt.bg_sel_col", self.__bg_sel)

        if self.__files:
            config.set(
                "myopt.lang1_file",
                os.path.basename(self.__files[self.__lang1]),
            )
            config.set(
                "myopt.lang2_file",
                os.path.basename(self.__files[self.__lang2]),
            )

        config.set("myopt.config_id", CONFIG_ID)
        config.set("myopt.config_schema", CONFIG_SCHEMA_VERSION)
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
            self.lang1_loc.clear()
            self.lang2_txt.clear()
            self.lang2_loc.clear()
            self.linenbr = 0

        with open(flnm, encoding="utf-8", newline="") as csvfile:
            reader = csv.reader(csvfile)

            for row in reader:
                self.linenbr += 1
                if self.linenbr == 1:
                    continue

                if len(row) < 8:
                    continue

                source = self.clean_translatable(row[1])
                target = row[2].strip()
                anchor = row[7].strip()

                if self.filenbr == 0:
                    self.lang1_txt[source] = target
                    self.lang1_loc[source] = anchor
                    self.lang2_txt[source] = ""
                else:
                    self.lang2_txt[source] = target
                    self.lang2_loc[source] = anchor

        if len(self.__fl_ar) == 1 or self.filenbr == 1:
            for key in self.lang2_txt:
                if key not in self.lang1_txt:
                    self.lang1_txt[key] = ""
                    self.lang1_loc[key] = self.lang2_loc.get(key, "")

            for key, value in self.lang1_txt.items():
                self.model.append(
                    (
                        key,
                        value,
                        self.lang1_loc.get(key, ""),
                        self.lang2_txt.get(key, ""),
                        self.__fg_sel,
                        self.__bg_sel,
                    )
                )

    # ------------------------------------------------------------------
    # Main / UI
    # ------------------------------------------------------------------

    def main(self):
        self.model.clear()
        self.set_fl_ar()

        self.gui.WIDGET.get_column(2).set_visible(self.__show_anchor)
        self.gui.WIDGET.get_column(3).set_visible(self.__lang1 != self.__lang2)

        self.gui.WIDGET.set_search_column(
            3 if self.__search_lang == 2 else 1
        )

        self.filenbr = 0
        for fl in self.__fl_ar:
            if os.path.isfile(fl):
                self.load_file(fl)
                self.filenbr += 1

    def act(self, _tree_view, path, _column):
        tree_iter = self.model.get_iter(path)
        link = self.model.get_value(tree_iter, 2).strip()

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
        self.model = Gtk.ListStore(str, str, str, str, str, str)
        view = Gtk.TreeView(self.model)
        view.connect("row-activated", self.act)

        renderer = Gtk.CellRendererText()

        view.append_column(
            Gtk.TreeViewColumn(_("English Term"), renderer, text=0, foreground=4, background=5)
        )
        view.append_column(
            Gtk.TreeViewColumn(_("Target"), renderer, text=1, foreground=4, background=5)
        )
        view.append_column(
            Gtk.TreeViewColumn(_("Anchor"), renderer, text=2, foreground=4, background=5)
        )
        view.append_column(
            Gtk.TreeViewColumn(_("Language 2"), renderer, text=3, foreground=4, background=5)
        )

        view.set_search_column(1)
        self.model.set_sort_column_id(0, Gtk.SortType.ASCENDING)

        self.set_tooltip(_("Double click row to open glossary entry"))
        return view
