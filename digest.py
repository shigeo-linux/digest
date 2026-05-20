#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import GLib, Gdk, Gtk, Gio

GLib.set_prgname('com.digest.app')
Gdk.set_program_class('com.digest.app')

from ui.main_window import MainWindow


class DigestApp(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id='com.digest.app',
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )

    def do_activate(self):
        existing = self.get_windows()
        if existing:
            existing[0].present()
            return
        win = MainWindow(self)
        win.show_all()

    def do_open(self, files, n_files, hint):
        existing = self.get_windows()
        if existing:
            win = existing[0]
            win.present()
        else:
            win = MainWindow(self)
            win.show_all()
        if files:
            path = files[0].get_path()
            if path:
                win._load_pdf(path)


def main():
    app = DigestApp()
    return app.run(sys.argv)


if __name__ == '__main__':
    sys.exit(main())
