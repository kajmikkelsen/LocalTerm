#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2024-2025 Kaj Mikkelsen <kmi@vgdata.dk>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# 20251008
# added strip to the dequote function
# added dictionaries
# filling gui from dictionary instead of from file
# 20251009
# added functionality for two languages
# cleaned up the setup
# 20251014
# Fixed issue with error when calling the URL
# changed header names
# 20251022
# Added more test files (Thanks Brian McCullogh)
# Changes filenames to csv
# verified that the file glob ignores case
# added the setup option of hiding the anchor column
# added the function of changing the anchor visibility in runtime
# 20251023
# if anchor starts with https:// the anchor becomes the URL other wise th URL is Combined from the baseurl in setup and the anchor
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
# ----------------------------------------------------------------------------
"""
Local term - a plugin for showing translatable terms
"""

# File: LocalTerm.py
# from gramps.gen.plug import Gramplet

import os
import logging
import glob
import gi
import gramps.gen.utils.alive as est

# from gramps.gen.utils.alive import update_constants
from gramps.gen.utils.alive import probably_alive_range
from gramps.gen.plug import Gramplet
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.version import VERSION as GRAMPSVERSION, VERSION_TUPLE
from gramps.gen.datehandler import parser
from gramps.gen.lib.date import Today

# from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback
from gramps.gen.config import config as configman
from gramps.gui.display import display_url
from gramps.gui.dialog import ErrorDialog
from gramps.gen.plug.menu import (
    BooleanOption,
    StringOption,
    BooleanListOption,
    ColorOption,
    NumberOption,
    EnumeratedListOption,
)

# from gi.repository import Pango

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

# ------------------------------------------------------------------------
#
# GRAMPS modules
#
# ------------------------------------------------------------------------

local_log = logging.getLogger("LocalTerm")
_level = os.environ.get("GRAMPS_LOG_LEVEL", "WARNING")
_level = "info"
if _level == "info":
    local_log.setLevel(logging.INFO)
else:
    local_log.setLevel(logging.WARNING)

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext
lang = glocale.lang
show_error = True
local_log.info("---> before any fuction is called")
# local_log.info("Maximum age = %s",_MAX_AGE_PROB_ALIVE);
_config_file = os.path.join(os.path.dirname(__file__), "data", "LocalTerm")

config = configman.register_manager(_config_file)
config.register("myopt.show_anchor", False)
config.register(
    "myopt.url_bas", "https://gramps-project.org/wiki/index.php/Gramps_Glossary"
)
config.register("myopt.search_lang", 1)
config.register("myopt.files", "en_US_localterm.txt")
config.register("myopt.fg_sel_col", "#000000")
config.register("myopt.bg_sel_col", "#ffffff")
config.register("myopt.lang1",0)
config.register("myopt.lang2",0)



class LocalTerm(Gramplet):
    """
    class for showing an index of translatable terms
    """

    # pylint: disable=too-many-instance-attributes

    def init(self):
        local_log.info("--> dette var init")
        config.load()
        self.gui.WIDGET = self.build_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.gui.WIDGET)
        self.gui.WIDGET.show()
        self.model.clear()
        flnam = os.path.join(os.path.dirname(__file__), "data", "*localterm.csv")
        self.__files = [f for f in glob.glob(flnam)]

        self.lang1_txt = {}
        self.lang2_txt = {}
        self.lang1_loc = {}
        self.lang2_loc = {}

    def build_options(self):
        """
        Build the configuration options.
        """
        local_log.info("--> build_options")
        self.opts = []

        name = _("The URL base the anchor will be attached to")
        opt = StringOption(name, self.__url_bas)
        self.opts.append(opt)
        name = _("Show anchor column")
        opt = BooleanOption(name, self.__show_anchor)
        self.opts.append(opt)
        name = _("Search language")
        opt = NumberOption(name, self.__search_lang, 1, 2, 1)
        self.opts.append(opt)
        name = _("Foreground color")
        opt = ColorOption(name, self.__fg_sel)
        self.opts.append(opt)
        name = _("Background color")
        opt = ColorOption(name, self.__bg_sel)
        self.opts.append(opt)
        local_log.info("files = %s", self.__files)
        opt = EnumeratedListOption(_("Language 1"),self.__lang1)
        i = 0
        for filnm in self.__files:
            short_fil_name = os.path.basename(filnm)
            opt.add_item(i,short_fil_name)
            i += 1
        self.opts.append(opt)
        opt = EnumeratedListOption(_("Language 2"),self.__lang2)
        i = 0
        for filnm in self.__files:
            short_fil_name = os.path.basename(filnm)
            opt.add_item(i,short_fil_name)
            i += 1
        self.opts.append(opt)
        self.set_fl_ar()
        local_log.info("chosen files =%s  %s",self.__files[self.__lang1],self.__files[self.__lang2 ])
        list(map(self.add_option, self.opts))

    def set_fl_ar(self):
        """
        set the file array based on the selected languages
        """
        self.__fl_ar = []
        self.__fl_ar.append(os.path.basename(self.__files[self.__lang1]))
        self.__url_ap = (os.path.basename(self.__files[self.__lang1]) ).split("_")[0]
        local_log.info("base for url = %s", self.__url_ap)
        if self.__lang2 != self.__lang1:
            self.__fl_ar.append(os.path.basename(self.__files[self.__lang2]))

    def save_options(self):
        """
        Save gramplet configuration data.
        """
        # pylint: disable=attribute-defined-outside-init
        local_log.info("--> save_options")
        self.__url_bas = self.opts[0].get_value()
        self.__show_anchor = self.opts[1].get_value()
        self.__search_lang = self.opts[2].get_value()
        self.__fg_sel = self.opts[3].get_value()
        self.__bg_sel = self.opts[4].get_value()
        self.__lang1 = self.opts[5].get_value()
        self.__lang2 = self.opts[6].get_value()
        self.set_fl_ar()

        local_log.info("lang1 = %s", self.__lang1)
        config.set("myopt.show_anchor", self.__show_anchor)
        config.set("myopt.url_bas", self.__url_bas)
        config.set("myopt.search_lang", self.__search_lang)
        config.set("myopt.fg_sel_col", self.__fg_sel)
        config.set("myopt.bg_sel_col", self.__bg_sel)
        local_log.info("lang1 = %s", self.__lang1)
        config.set("myopt.lang1",self.__lang1)
        config.set("myopt.lang2",self.__lang2)

        local_log.info("lang1  nu = %s", self.__lang1)
        if len(self.__fl_ar) > 2:
            errormessage = _("Max two files can be selecteda")
            ErrorDialog(_("Error:"), errormessage)
        else:
            config.save()

    def save_update_options(self, obj):
        """
        Save a gramplet's options to file.
        """
        local_log.info("--> save_update_options")
        self.save_options()
        self.update()

    def on_load(self):
        """
        Load stored configuration data.
        """
        local_log.info("--> on_load function")
        self.__show_error = True
        self.__show_anchor = config.get("myopt.show_anchor")
        self.__search_lang = config.get("myopt.search_lang")
        self.__url_bas = config.get("myopt.url_bas")
        self.__fg_sel = config.get("myopt.fg_sel_col")
        self.__bg_sel = config.get("myopt.bg_sel_col")
        self.__lang1 = config.get("myopt.lang1")
        self.__lang2 = config.get("myopt.lang2")
        local_log.info("lang1 i load = %s", self.__lang1)

    def dequote(self, s):
        """
        If a string has single or double quotes around it, remove them.
        Make sure the pair of quotes match.
        If a matching pair of quotes is not found,
        or there are less than 2 characters, return the string unchanged.
        """
        s = s.strip()
        if (len(s) >= 2 and s[0] == s[-1]) and s.startswith(("'", '"')):
            return s[1:-1]
        return s

    def clean_translatable(self, s):
        """
        if s starts with '_(' and ends with ')' remove these
        """
        s = self.dequote(s)
        if s.startswith("_(") and s.endswith(")"):
            return s[2:-1].strip()
        return s

    def load_file(self, flnm):
        """
        loading the file into the treeview
        """
        local_log.info("--> load file %s", flnm)
        self.sort_date = ""
        if self.filenbr == 0:
            self.lang1_txt.clear()
            self.lang1_loc.clear()
            self.lang2_txt.clear()
            self.lang2_loc.clear()
        self.linenbr = 0
        with open(flnm, encoding="utf-8") as myfile:
            for line in myfile:
                self.linenbr += 1
                if self.linenbr > 1:
                    line = line.rstrip() + ","
                    words = line.split(",")
                    if len(words) != 4:
                        if len(line) > 10:
                            errormessage = (
                                _(
                                    ': line does not contain three sections separated by , in : "'
                                )
                                + line
                                + 'i" File: '
                                + flnm
                            )
                            errormessage = str(self.linenbr) + errormessage
                            ErrorDialog(_("Error:"), errormessage)
                    else:
                        words[0] = self.dequote(words[0])
                        words[1] = self.clean_translatable(words[1])
                        words[1] = self.dequote(words[1])

                        if self.filenbr == 0:
                            self.lang1_txt[words[1]] = words[0]
                            self.lang1_loc[words[1]] = words[2]
                            self.lang2_txt[words[1]] = ""
                        else:
                            self.lang2_txt[words[1]] = words[0]
                            self.lang2_loc[words[1]] = words[2]

        if (len(self.__fl_ar) == 1) or (self.filenbr == 1):
            for key1, value1 in self.lang2_loc.items():
                if not key1 in self.lang1_txt:
                    self.lang1_loc[key1] = value1
                    self.lang1_txt[key1] = ""

            for key, value in self.lang1_txt.items():
                mytupple = (
                    key,
                    value,
                    self.lang1_loc.get(key, "not found"),
                    self.lang2_txt.get(key, "not found"),
                    self.__fg_sel,
                    self.__bg_sel,
                )
                self.model.append(mytupple)

    def main(self):
        self.model.clear()
        col = self.gui.WIDGET.get_column(2)
        col.set_visible(self.__show_anchor)
        col = self.gui.WIDGET.get_column(3)
        if self.__lang1 == self.__lang2:
            col.set_visible(False)
        else:
            col.set_visible(True)

#        col.set_visible(self.__lang1 == self.__lang2)
        local_log.info("Languages = %s  %s", self.__lang1, self.__lang2)
        if self.__search_lang == 2:
            self.gui.WIDGET.set_search_column(3)
        else:
            self.gui.WIDGET.set_search_column(1)
        local_log.info("--> Main kaldet")
        local_log.info("files to load = %s", self.__fl_ar)
        self.filenbr = 0
#        self.__files = []
        for flnm in self.__fl_ar:
            flnm = os.path.join(os.path.dirname(__file__), "data", flnm)
            if not os.path.exists(flnm):
                flnm = os.path.join(
                    os.path.dirname(__file__), "default" + "_data_v1_0.txt"
                )
            if os.path.exists(flnm):
                if os.path.isfile(flnm):
                    self.load_file(flnm)
                    self.filenbr = self.filenbr + 1
                else:
                    self.set_text("No file " + flnm)
            else:
                self.set_text("No path " + flnm)

    def act(self, _tree_view, path, _column):
        """
        Called when the user double-click a row
        """
        local_log.info("--> act called")
        tree_iter = self.model.get_iter(path)
        url = self.model.get_value(tree_iter, 2).strip()
        if not url.startswith("https://"):
            url = self.__url_bas + "#" + url
        local_log.info("URL after processing: %s", url)
        if url.startswith("https://"):
            display_url(url)
        else:
            errormessage = _("Cannot open URL: ") + url
            ErrorDialog(_("Error:"), errormessage)

    def build_gui(self):
        """
        Build the GUI interface.
        """
        local_log.info("--> build gui")
        self.__show_anchor = config.get("myopt.show_anchor")
        self.__search_lang = config.get("myopt.search_lang")
        self.__lang1 = config.get("myopt.lang1")
        self.__lang2 = config.get("myopt.lang2")
        local_log.info(self.__show_anchor)
        tip = _("Double click row to follow link")
        self.set_tooltip(tip)
        self.model = Gtk.ListStore(str, str, str, str, str, str)
        top = Gtk.TreeView()
        top.connect("row-activated", self.act)
        renderer = Gtk.CellRendererText()

        column = Gtk.TreeViewColumn(
            _("Translatable"), renderer, text=0, foreground=4, background=5
        )
        column.set_sort_column_id(0)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        top.append_column(column)

        column = Gtk.TreeViewColumn(
            _("Language 1"), renderer, text=1, foreground=4, background=5
        )
        column.set_sort_column_id(1)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

        top.append_column(column)
        column = Gtk.TreeViewColumn(
            _("Anchor"), renderer, text=2, foreground=4, background=5
        )
        column.set_sort_column_id(2)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        if self.__show_anchor:
            column.set_visible(True)
        else:
            column.set_visible(False)

        top.append_column(column)

        column = Gtk.TreeViewColumn(
            _("Language 2"), renderer, text=3, foreground=4, background=5
        )
        column.set_sort_column_id(3)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        if self.__lang1 == self.__lang2:
            column.set_visible(False)
        else:
            column.set_visible(True)

#        column.set_visible((self.__lang1 == self.__lang2))
        local_log.info("Languages = %s  %s", self.__lang1, self.__lang2)

        top.append_column(column)

        self.model.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        top.set_model(self.model)
        if self.__search_lang == 2:
            top.set_search_column(3)
        else:
            top.set_search_column(1)
        return top
