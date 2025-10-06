#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2024 Kaj Mikkelsen <kmi@vgdata.dk>
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

# ----------------------------------------------------------------------------
"""
    Local term - a plugin for showing translatable terms
    Will show the person in a historical context
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
local_log.info("Sprog = %s", lang)
show_error = True
# local_log.info("Maximum age = %s",_MAX_AGE_PROB_ALIVE);
_config_file = os.path.join(os.path.dirname(__file__), "LocalTerm")

config = configman.register_manager(_config_file)
config.register("myopt.filter_text", "Filter out")
config.register("myopt.use_filter", False)
config.register("myopt.show_outside_span", True)
config.register("myopt.files", "default_data_v1_0.txt")
config.register("myopt.fg_sel_col", "#000000")
config.register("myopt.bg_sel_col", "#ffffff")
config.register("myopt.fg_usel_col", "#000000")
config.register("myopt.bg_usel_col", "#ededed")
config.register("myopt.fl_ar", ["default_data_v1_0.txt"])
config.register("myopt.use_full_date", False)


class LocalTerm(Gramplet):
    """
    class for showing a timeline
    """

    # pylint: disable=too-many-instance-attributes

    def init(self):
        local_log.info("--> dette var init")
        # local_log.info("version: %s",HistContext.)
        #        self.gui.model = Gtk.ListStore(str, str, str, str, str)
        self.gui.WIDGET = self.build_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.gui.WIDGET)
        self.gui.WIDGET.show()
        self.model.clear()
        config.load()

    def build_options(self):
        """
        Build the configuration options.
        """

        files = []
        self.opts = []

        name = _("Rows starting with this in the text column will be hidden ")
        opt = StringOption(name, self.__start_filter_st)
        self.opts.append(opt)
        name = _("Use filter ")
        opt = BooleanOption(name, self.__use_filter)
        self.opts.append(opt)
        name = _("Show outside life span ")
        opt = BooleanOption(name, self.__show_it)
        self.opts.append(opt)
        name = _("Use full dates")
        opt = BooleanOption(name, self.__use_full_date)
        self.opts.append(opt)
        name = _("Foreground color items in lifespan")
        opt = ColorOption(name, self.__fg_sel)
        self.opts.append(opt)
        name = _("Background color items in lifespan")
        opt = ColorOption(name, self.__bg_sel)
        self.opts.append(opt)
        name = _("Foreground color items outside lifespan")
        opt = ColorOption(name, self.__fg_not_sel)
        self.opts.append(opt)
        name = _("Background color items outside lifespan")
        opt = ColorOption(name, self.__bg_not_sel)
        self.opts.append(opt)
        flnam = os.path.join(os.path.dirname(__file__), "*localterm.txt")
        files = [f for f in glob.glob(flnam)]
        opt = BooleanListOption(_("Select from files"))
        for filnm in files:
            short_fil_name = os.path.basename(filnm)
            bol_val = short_fil_name in self.__fl_ar
            opt.add_button(os.path.basename(filnm), bol_val)
        self.opts.append(opt)
        list(map(self.add_option, self.opts))

    def save_options(self):
        """
        Save gramplet configuration data.
        """
        # pylint: disable=attribute-defined-outside-init
        self.__start_filter_st = self.opts[0].get_value()
        self.__use_filter = self.opts[1].get_value()
        self.__show_it = self.opts[2].get_value()
        self.__use_full_date = self.opts[3].get_value()
        self.__use_year = not self.__use_full_date
        self.__fg_sel = self.opts[4].get_value()
        self.__bg_sel = self.opts[5].get_value()
        self.__fg_not_sel = self.opts[6].get_value()
        self.__bg_not_sel = self.opts[7].get_value()
        self.__fl_ar = self.opts[8].get_selected()
        config.set("myopt.filter_text", self.__start_filter_st)
        config.set("myopt.use_filter", self.__use_filter)
        config.set("myopt.show_outside_span", self.__show_it)
        config.set("myopt.use_full_date", self.__use_full_date)
        config.set("myopt.fg_sel_col", self.__fg_sel)
        config.set("myopt.bg_sel_col", self.__bg_sel)
        config.set("myopt.fg_usel_col", self.__fg_not_sel)
        config.set("myopt.bg_usel_col", self.__bg_not_sel)
        config.set("myopt.fl_ar", self.__fl_ar)
        config.save()

    def save_update_options(self, obj):
        """
        Save a gramplet's options to file.
        """
        self.save_options()
        self.update()

    def on_load(self):
        """
        Load stored configuration data.
        """
        self.__show_error = True
        local_log.info("Antal = %d", len(self.gui.data))
        self.__start_filter_st = config.get("myopt.filter_text")
        self.__use_filter = config.get("myopt.use_filter")
        self.__show_it = config.get("myopt.show_outside_span")
        self.__use_full_date = config.get("myopt.use_full_date")
        self.__use_year = not self.__use_full_date
        self.__fg_sel = config.get("myopt.fg_sel_col")
        self.__bg_sel = config.get("myopt.bg_sel_col")
        self.__fg_not_sel = config.get("myopt.fg_usel_col")
        self.__bg_not_sel = config.get("myopt.bg_usel_col")
        self.__fl_ar = config.get("myopt.fl_ar")

    #        if self.__fl_ar[0] == "None":
    #           self.__fl_ar[0] = os.path.basename(self.__sel_file)

    def dequote(self,s):
        """
        If a string has single or double quotes around it, remove them.
        Make sure the pair of quotes match.
        If a matching pair of quotes is not found,
        or there are less than 2 characters, return the string unchanged.
        """
        if (len(s) >= 2 and s[0] == s[-1]) and s.startswith(("'", '"')):
            return s[1:-1]
        return s

    def load_file(self, flnm):
        """
        loading the file into the treeview
        """
        local_log.info("FILENANME %s", flnm)
        self.sort_date = ""

        self.linenbr = 0
        with open(flnm, encoding="utf-8") as myfile:
            for line in myfile:
                self.linenbr += 1
                line = line.rstrip() + ","
                words = line.split(",")
                local_log.info("number words %d",len(words))
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
                        mytupple = (
                            words[0],
                            words[1].replace("'",""),
                            words[2],
                            '',
                            self.__fg_sel,
                            self.__bg_sel,
                        )
                        self.model.append(mytupple)

    def main(self):
        self.model.clear()
        local_log.info("Main kaldet")
        for flnm in self.__fl_ar:
            flnm = os.path.join(os.path.dirname(__file__), flnm)
            if not os.path.exists(flnm):
                flnm = os.path.join(
                    os.path.dirname(__file__), "default" + "_data_v1_0.txt"
                )
            if os.path.exists(flnm):
                if os.path.isfile(flnm):
                    self.load_file(flnm)
                else:
                    self.set_text("No file " + flnm)
            else:
                self.set_text("No path " + flnm)

    def active_changed(self, handle):
        """
        Called when the active person is changed.
        """
        local_log.info("Active changed")
        self.update()

    def act(self, _tree_view, path, _column):
        """
        Called when the user double-click a row
        """
        tree_iter = self.model.get_iter(path)
#        url = self.model.get_value(tree_iter, 4)
        if url.startswith("https://"):
            display_url(url)
        else:
            errormessage = _("Cannot open URL: ") + url
            ErrorDialog(_("Error:"), errormessage)

    def build_gui(self):
        """
        Build the GUI interface.
        """
        local_log.info("-->build gui")
        tip = _("Double click row to follow link")
        self.set_tooltip(tip)
        # pylint: disable=attribute-defined-outside-init
        # define array from_date, to_date, Eventsdescription, link to internet, sort_date, foreground_colour, backgroud_colour
        # Only first three comlumns are visible
        self.model = Gtk.ListStore(str, str, str, str, str, str)
        top = Gtk.TreeView()
        top.connect("row-activated", self.act)
        renderer = Gtk.CellRendererText()

        column = Gtk.TreeViewColumn(
            _("Term"), renderer, text=0, foreground=4, background=5
        )
        #        column.set_expand(False)
        #        column.set_resizable(True)
        #        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        #        column.set_fixed_width(50)
        column.set_sort_column_id(0)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        top.append_column(column)

        column = Gtk.TreeViewColumn(
            _("Translatable"), renderer, text=1, foreground=4, background=5
        )
        column.set_sort_column_id(1)
        #        column.set_fixed_width(50)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

        top.append_column(column)

        column = Gtk.TreeViewColumn(
            _("Local"), renderer, text=2, foreground=4, background=5
        )
        column.set_sort_column_id(2)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        top.append_column(column)

        # column = Gtk.TreeViewColumn(
        #    _("Dato"), renderer, text=3, foreground=5, background=6
        # )
        #        column.set_sort_column_id(3)
        #        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        #        top.append_column(column)

        #        column = Gtk.TreeViewColumn(_('Link'), renderer, text=3,foreground=4,background=5)
        #        column.set_sort_column_id(3)
        #        column.set_fixed_width(150)
        #        top.append_column(column)
        self.model.set_sort_column_id(3, Gtk.SortType.ASCENDING)
        top.set_model(self.model)
        return top
