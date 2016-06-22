#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Launching of programs, folders, URLs, etc.."""
from __future__ import print_function, unicode_literals, absolute_import

import sys
import os
import subprocess
import copy

from .helpers import get_resource
from .lnp import lnp
from . import hacks, paths, log

def get_configured_terminal():
    """Retrieves the configured terminal command."""
    return lnp.userconfig.get_string('terminal')

def configure_terminal(new_path):
    """Configures the command used to launch a terminal on Linux."""
    lnp.userconfig['terminal'] = new_path
    lnp.userconfig.save_data()

def toggle_autoclose():
    """Toggle automatic closing of the UI when launching DF."""
    lnp.userconfig['autoClose'] = not lnp.userconfig.get_bool('autoClose')
    lnp.userconfig.save_data()

def get_df_executable():
    """Returns the path of the executable needed to launch Dwarf Fortress."""
    spawn_terminal = False
    if sys.platform == 'win32':
        if ('legacy' in lnp.df_info.variations and
                lnp.df_info.version <= '0.31.14'):
            df_filename = 'dwarfort.exe'
        else:
            df_filename = 'Dwarf Fortress.exe'
    elif sys.platform == 'darwin' and lnp.df_info.version <= '0.28.181.40d':
        df_filename = 'Dwarf Fortress.app'
    else:
        # Linux/OSX: Run DFHack if available and enabled
        if (os.path.isfile(paths.get('df', 'dfhack')) and
                hacks.is_dfhack_enabled()):
            df_filename = 'dfhack'
            spawn_terminal = True
        else:
            df_filename = 'df'
    if lnp.args.df_executable:
        df_filename = lnp.args.df_executable
    return df_filename, spawn_terminal

def run_df(force=False):
    """Launches Dwarf Fortress."""
    validation_result = lnp.settings.validate_config()
    if validation_result:
        if not lnp.ui.on_invalid_config(validation_result):
            return
    df_filename, spawn_terminal = get_df_executable()

    executable = paths.get('df', df_filename)
    result = run_program(executable, force, True, spawn_terminal)
    if (force and not result) or result is False:
        log.e('Could not launch ' + executable)
        raise Exception('Failed to run Dwarf Fortress.')

    for prog in lnp.autorun:
        utility = paths.get('utilities', prog)
        if os.access(utility, os.F_OK):
            run_program(utility)

    if lnp.userconfig.get_bool('autoClose'):
        sys.exit()
    return result

def get_terminal_launcher():
    """Returns a command prefix to launch a program in a new terminal."""
    if sys.platform == 'darwin':
        return ['open', '-a', 'Terminal.app']
    elif sys.platform.startswith('linux'):
        override = get_configured_terminal()
        if override:
            return override.split(' ')
        return [get_resource('xdg-terminal')]
    raise Exception('No terminal launcher for platform: ' + sys.platform)

def run_program(path, force=False, is_df=False, spawn_terminal=False):
    """
    Launches an external program.

    Params:
        path
            The path of the program to launch.
        spawn_terminal
            Whether or not to spawn a new terminal for this app.
            Used only for DFHack.
    """
    path = os.path.abspath(path)
    check_nonchild = ((spawn_terminal and sys.platform.startswith('linux')) or
                      (sys.platform == 'darwin' and (
                          path.endswith('.app') or spawn_terminal)))

    is_running = program_is_running(path, check_nonchild)
    if not force and is_running:
        log.i(path + ' is already running')
        lnp.ui.on_program_running(path, is_df)
        return None

    try:
        workdir = os.path.dirname(path)
        # pylint:disable=redefined-variable-type
        run_args = path
        if spawn_terminal and not sys.platform.startswith('win'):
            term = get_terminal_launcher()
            if "$" in term:
                cmd = [path if x == '$' else x for x in term]
            else:
                cmd = term + [path]
            retcode = subprocess.call(cmd, cwd=workdir)
            return retcode == 0
        elif path.endswith('.jar'):  # Explicitly launch JAR files with Java
            run_args = ['java', '-jar', os.path.basename(path)]
        elif path.endswith('.app'):  # OS X application bundle
            run_args = ['open', path]
            workdir = path

        environ = os.environ
        if lnp.bundle:
            environ = copy.deepcopy(os.environ)
            if ('TCL_LIBRARY' in environ and
                    sys._MEIPASS in environ['TCL_LIBRARY']): # pylint:disable=no-member
                del environ['TCL_LIBRARY']
            if ('TK_LIBRARY' in environ and
                    sys._MEIPASS in environ['TK_LIBRARY']): # pylint:disable=no-member
                del environ['TK_LIBRARY']

        lnp.running[path] = subprocess.Popen(
            run_args, cwd=workdir, env=environ)
        return True
    except OSError:
        sys.excepthook(*sys.exc_info())
        return False

def program_is_running(path, nonchild=False):
    """
    Returns True if a program is currently running.

    Params:
        path
            The path of the program.
        nonchild
            If set to True, attempts to check for the process among all
            running processes, not just known child processes. Used for
            DFHack on Linux and OS X; currently unsupported for Windows.
    """
    if nonchild:
        ps = subprocess.Popen(['ps', 'axww'], stdout=subprocess.PIPE)
        s = ps.stdout.read()
        ps.wait()
        encoding = sys.getfilesystemencoding()
        if encoding is None:
            #Encoding was not detected, assume UTF-8
            encoding = 'UTF-8'
        return path in s.decode(encoding, 'replace')
    else:
        if path not in lnp.running:
            return False
        else:
            lnp.running[path].poll()
            return lnp.running[path].returncode is None

def open_folder_idx(i):
    """Opens the folder specified by index i, as listed in PyLNP.json."""
    open_file(os.path.join(
        paths.get('root'), lnp.config['folders'][i][1].replace(
            '<df>', paths.get('df'))))

def open_savegames():
    """Opens the save game folder."""
    open_file(paths.get('save'))

def open_link_idx(i):
    """Opens the link specified by index i, as listed in PyLNP.json."""
    open_url(lnp.config['links'][i][1])

def open_url(url):
    """Launches a web browser to the Dwarf Fortress webpage."""
    import webbrowser
    webbrowser.open(url)

def open_file(path):
    """
    Opens a file with the system default viewer for the respective file type.

    Params:
        path
            The file path to open.
    """
    path = os.path.normpath(path)
    # pylint: disable=broad-except, bare-except
    try:
        if sys.platform == 'darwin':
            subprocess.check_call(['open', '--', path])
        elif sys.platform.startswith('linux'):
            subprocess.check_call(['xdg-open', path])
        elif sys.platform in ['windows', 'win32']:
            os.startfile(path)
        else:
            log.e('Unknown platform, cannot open file')
    except:
        log.e('Could not open file ' + path)

def get_valid_terminals():
    """Gets the terminals that are available on this system."""
    def get_subclasses(c):
        """Returns all subclasses of <c>, direct and indirect."""
        result = []
        for s in c.__subclasses__():
            result.append(s)
            result += get_subclasses(s)
        return result

    terminals = get_subclasses(LinuxTerminal)

    for t in terminals:
        log.d("Checking for terminal %s", t.name)
        if t.detect():
            log.d("Found terminal %s", t.name)

class LinuxTerminal(object):
    """
    Class for detecting and launching using a dedicated terminal on Linux.
    """

    # Set this in subclasses to provide a label for the terminal.
    name = "????"

    @staticmethod
    def detect():
        """Detects if this terminal is available."""
        pass

    @staticmethod
    def get_command_line():
        """
        Returns a subprocess-compatible command to launch a command with
        this terminal.
        If the command to be launched should go somewhere other than the end
        of the command line, use $ to indicate the correct place.
        """
        pass

# pylint: disable=missing-docstring, bare-except

# Desktop environment-specific terminals
class KDETerminal(LinuxTerminal):
    name = "KDE"

    @staticmethod
    def detect():
        return os.environ.get('KDE_FULL_SESSION', '') == 'true'

    @staticmethod
    def get_command_line():
        s = subprocess.check_output(
            ['kreadconfig', '--file', 'kdeglobals', '--group', 'General',
             '--key', 'TerminalApplication', '--default', 'konsole'])
        return ['nohup', s, '-e']

class GNOMETerminal(LinuxTerminal):
    name = "GNOME"

    @staticmethod
    def detect():
        if os.environ.get('GNOME_DESKTOP_SESSION_ID', ''):
            return True
        FNULL = open(os.devnull, 'w')
        try:
            return subprocess.call(
                [
                    'dbus-send', '--print-reply', '--dest=org.freedesktop.DBus',
                    '/org/freedesktop/DBus org.freedesktop.DBus.GetNameOwner',
                    'string:org.gnome.SessionManager'
                ], stdout=FNULL, stderr=FNULL) == 0
        except:
            return False
        finally:
            FNULL.close()

    @staticmethod
    def get_command_line():
        term = subprocess.check_output([
            'gconftool-2', '--get',
            '/desktop/gnome/applications/terminal/exec'])
        term_arg = subprocess.check_output([
            'gconftool-2', '--get',
            '/desktop/gnome/applications/terminal/exec_arg'])
        return ['nohup', term, term_arg]

class XfceTerminal(LinuxTerminal):
    name = "Xfce"

    @staticmethod
    def detect():
        try:
            s = subprocess.check_output(
                ['ps', '-eo', 'comm='], stderr=subprocess.STDOUT)
            return 'xfce' in s
        except:
            return False

    @staticmethod
    def get_command_line():
        return ['nohup', 'exo-open', '--launch', 'TerminalEmulator']

class LXDETerminal(LinuxTerminal):
    name = "LXDE"

    @staticmethod
    def detect():
        if not os.environ.get('DESKTOP_SESSION', '') == 'LXDE':
            return False
        FNULL = open(os.devnull, 'w')
        try:
            return subprocess.call(
                ['which', 'lxterminal'], stdout=FNULL, stderr=FNULL,
                close_fds=True) == 0
        except:
            return False
        finally:
            FNULL.close()

    @staticmethod
    def get_command_line():
        return ['nohup', 'lxterminal', '-e']

class MateTerminal(LinuxTerminal):
    name = "MATE"

    @staticmethod
    def detect():
        if os.environ.get('MATE_DESKTOP_SESSION_ID', ''):
            return True
        FNULL = open(os.devnull, 'w')
        try:
            return subprocess.call(
                [
                    'dbus-send', '--print-reply', '--dest=org.freedesktop.DBus',
                    '/org/freedesktop/DBus org.freedesktop.DBus.GetNameOwner',
                    'string:org.mate.SessionManager'
                ], stdout=FNULL, stderr=FNULL) == 0
        except:
            return False
        finally:
            FNULL.close()
    @staticmethod
    def get_command_line():
        return ['nohup', 'mate-terminal', '-e']

class i3Terminal(LinuxTerminal):
    name = "i3"

    @staticmethod
    def detect():
        return os.environ.get('DESKTOP_STARTUP_ID', '').startswith('i3/')

    @staticmethod
    def get_command_line():
        return ['nohup', 'i3-sensible-terminal', '-e']

# Generic terminals (rxvt, xterm, etc.)
class rxvtTerminal(LinuxTerminal):
    name = "rxvt/urxvt"

    @staticmethod
    def detect():
        FNULL = open(os.devnull, 'w')
        try:
            if subprocess.call(
                    ['which', 'urxvt'], stdout=FNULL, stderr=FNULL) == 0:
                rxvtTerminal.exe = 'urxvt'
                return True
            if subprocess.call(
                    ['which', 'rxvt'], stdout=FNULL, stderr=FNULL) == 0:
                rxvtTerminal.exe = 'rxvt'
                return True
        except:
            return False
        finally:
            FNULL.close()

    @staticmethod
    def get_command_line():
        return ['nohup', rxvtTerminal.exe, '-e']

class xtermTerminal(LinuxTerminal):
    name = "xterm"

    @staticmethod
    def detect():
        FNULL = open(os.devnull, 'w')
        try:
            return subprocess.call(
                ['which', 'xterm'], stdout=FNULL, stderr=FNULL,
                close_fds=True) == 0
        except:
            return False
        finally:
            FNULL.close()

    @staticmethod
    def get_command_line():
        return ['nohup', 'xterm', '-e']

class CustomTerminal(LinuxTerminal):
    name = "Custom command"

    @staticmethod
    def detect():
        # Custom commands are always an option
        return True

    @staticmethod
    def get_command_line():
        cmd = get_configured_terminal()
        if cmd:
            cmd = cmd.split(' ')
        return cmd
