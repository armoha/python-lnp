#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint:disable=unused-wildcard-import,wildcard-import,invalid-name,attribute-defined-outside-init
"""Mods tab for the TKinter GUI."""
from __future__ import print_function, unicode_literals, absolute_import

import sys

from . import controls
from .layout import GridLayouter
from .tab import Tab
from core import mods

if sys.version_info[0] == 3:  # Alternate import names
    # pylint:disable=import-error
    from tkinter import *
    from tkinter.ttk import *
    import tkinter.messagebox as messagebox
    import tkinter.simpledialog as simpledialog
else:
    # pylint:disable=import-error
    from Tkinter import *
    from ttk import *
    import tkMessageBox as messagebox
    import tkSimpleDialog as simpledialog

#pylint: disable=too-many-public-methods
class ModsTab(Tab):
    """Mods tab for the TKinter GUI."""
    def create_variables(self):
        self.installed = Variable()
        self.available = Variable()
        self.status = 3

    def read_data(self):
        mods.clear_temp()
        available = mods.read_mods()
        installed = mods.get_installed_mods_from_log()
        available = [m for m in available if m not in installed]
        self.available.set(tuple(available))
        self.installed.set(tuple(installed))

    def create_controls(self):
        Grid.columnconfigure(self, 0, weight=1, uniform="mods")
        Grid.columnconfigure(self, 1, weight=1, uniform="mods")
        Grid.rowconfigure(self, 0, weight=1)
        Grid.rowconfigure(self, 2, weight=1)
        main_grid = GridLayouter(2)

        f = controls.create_control_group(self, 'Merged')
        install_frame, self.installed_list = controls.create_file_list(
            f, None, self.installed, selectmode='multiple')

        self.installed_list.bind(
            "<Double-1>", lambda e: self.remove_from_installed())
        reorder_frame = controls.create_control_group(install_frame, None)
        controls.create_trigger_button(
            reorder_frame, '↑', 'Move up', self.move_up).pack()
        controls.create_trigger_button(
            reorder_frame, '↓', 'Move down', self.move_down).pack()
        reorder_frame.grid(row=0, column=2, sticky="nse")

        main_grid.add(f, 2)

        main_grid.add(controls.create_trigger_button(
            self, '⇑', 'Add', self.add_to_installed))
        main_grid.add(controls.create_trigger_button(
            self, '⇓', 'Remove', self.remove_from_installed))

        f = controls.create_control_group(self, 'Available')
        _, self.available_list = controls.create_file_list(
            f, None, self.available, selectmode='multiple')
        self.available_list.bind(
            "<Double-1>", lambda e: self.add_to_installed())
        main_grid.add(f, 2)

        main_grid.add(controls.create_trigger_button(
            self, 'Install Mods', 'Copy merged mods to DF folder.',
            self.install_mods))
        main_grid.add(controls.create_trigger_option_button(
            self, 'Premerge Graphics',
            'Whether to start with the current graphics pack, or '
            'vanilla (ASCII) raws', self.toggle_preload, 'premerge_graphics',
            lambda v: ('NO', 'YES')[mods.will_premerge_gfx()]))
        main_grid.add(controls.create_trigger_button(
            self, 'Simplify Mods', 'Removes unnecessary files.',
            self.simplify_mods))
        main_grid.add(controls.create_trigger_button(
            self, 'Extract Installed', 'Creates a mod from unique changes '
            'to your installed raws.  Use to preserve custom tweaks.',
            self.create_from_installed))

    @staticmethod
    def toggle_preload():
        """Toggles whether to preload graphics before merging mods."""
        mods.toggle_premerge_gfx()

    def move_up(self):
        """Moves the selected item/s up in the merge order and re-merges."""
        if len(self.installed_list.curselection()) == 0:
            return
        selection = [int(i) for i in self.installed_list.curselection()]
        newlist = list(self.installed_list.get(0, END))
        for i in range(1, len(newlist)):
            j = i
            while j in selection and i-1 not in selection and j < len(newlist):
                newlist[j-1], newlist[j] = newlist[j], newlist[j-1]
                j += 1
        self.installed_list.delete(0, END)
        for i in newlist:
            self.installed_list.insert(END, i)
        first_missed = False
        for i in range(0, len(newlist)):
            if i not in selection:
                first_missed = True
            else:
                self.installed_list.select_set(i - int(first_missed))
        self.perform_merge()

    def move_down(self):
        """Moves the selected item/s down in the merge order and re-merges."""
        if len(self.installed_list.curselection()) == 0:
            return
        selection = [int(i) for i in self.installed_list.curselection()]
        newlist = list(self.installed_list.get(0, END))
        for i in range(len(newlist) - 1, 0, -1):
            j = i
            while i not in selection and j-1 in selection and j > 0:
                newlist[j-1], newlist[j] = newlist[j], newlist[j-1]
                j -= 1
        self.installed_list.delete(0, END)
        for i in newlist:
            self.installed_list.insert(END, i)
        first_missed = False
        for i in range(len(newlist), 0, -1):
            if i - 1 not in selection:
                first_missed = True
            else:
                self.installed_list.select_set(i - 1 + int(first_missed))
        self.perform_merge()

    def create_from_installed(self):
        """Extracts a mod from the currently installed raws."""
        if mods.make_mod_from_installed_raws('') is not None:
            name = simpledialog.askstring("Create Mod", "New mod name:")
            if name:
                if mods.make_mod_from_installed_raws(name):
                    messagebox.showinfo('Mod extracted',
                                        'Your mod was extracted as ' + name)
                else:
                    messagebox.showinfo(
                        'Error', 'There is already a mod with that name.')
                self.read_data()
        else:
            messagebox.showinfo('Error', 'No unique mods were found.')

    def add_to_installed(self):
        """Move selected mod/s from available to merged list and re-merge."""
        if len(self.available_list.curselection()) == 0:
            return
        for i in self.available_list.curselection():
            self.installed_list.insert(END, self.available_list.get(i))
        for i in self.available_list.curselection()[::-1]:
            self.available_list.delete(i)
        self.perform_merge()

    def remove_from_installed(self):
        """Move selected mod/s from merged to available list and re-merge."""
        if len(self.installed_list.curselection()) == 0:
            return
        for i in self.installed_list.curselection()[::-1]:
            self.available_list.insert(END, self.installed_list.get(i))
            self.installed_list.delete(i)
        #Re-sort items
        temp_list = sorted(list(self.available_list.get(0, END)))
        self.available_list.delete(0, END)
        for item in temp_list:
            self.available_list.insert(END, item)
        self.perform_merge()

    def perform_merge(self):
        """Merge the selected mods, with background color for user feedback."""
        from .tkgui import TkGui
        if not TkGui.check_vanilla_raws():
            return
        colors = ['pale green', 'yellow', 'orange', 'red', 'white']
        result = mods.merge_all_mods(self.installed_list.get(0, END))
        for i, status in enumerate(result):
            self.installed_list.itemconfig(i, bg=colors[status])
        self.status = max(result + [0])

    def install_mods(self):
        """Replaces <df>/raw with the contents LNP/Baselines/temp/raw"""
        if messagebox.askokcancel(
                message=('Your raws will be changed.\n\n'
                         'The mod merging function is still in beta.  This '
                         'could break new worlds, or even cause crashes.\n\n'
                         'Changing mods or graphics later might break a save, '
                         'so keep backups of everything you care about!'),
                title='Are you sure?'):
            if self.status < 2:
                if mods.install_mods():
                    messagebox.showinfo(
                        'Mods installed',
                        'The selected mods were installed.\nGenerate a new '
                        'world to start playing with them!')
                else:
                    messagebox.showinfo(
                        'Mods not installed',
                        'No mods were merged to install.')
            else:
                messagebox.showinfo(
                    'Mods not ready',
                    'The selected mods have merge confilcts and should not be '
                    'installed.\n\nResolve merge issues and try again.')

    @staticmethod
    def simplify_mods():
        """Simplify mods; runs on startup if called directly by button."""
        from .tkgui import TkGui
        if not TkGui.check_vanilla_raws():
            return
        m, f = mods.simplify_mods()
        messagebox.showinfo(
            str(m) + ' mods simplified',
            str(f) + ' files were removed from ' + str(m) + ' mods.')
