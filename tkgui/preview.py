#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint:disable=unused-wildcard-import,wildcard-import,invalid-name,attribute-defined-outside-init
"""Preview function for image sets."""
from __future__ import (
    print_function, unicode_literals, absolute_import, division)

import sys, os

from .child_windows import ChildWindow
from core import paths, colors, log, dfraw, graphics
from core.lnp import lnp
#pylint:disable=redefined-builtin
from io import open

if sys.version_info[0] == 3:  # Alternate import names
    # pylint:disable=import-error
    from tkinter import *
    from tkinter.ttk import *
else:
    # pylint:disable=import-error
    from Tkinter import *
    from ttk import *

# Workaround to use Pillow in PyInstaller
import pkg_resources  # pylint:disable=unused-import

try:  # PIL-compatible library (e.g. Pillow); used to load PNG images (optional)
    # pylint:disable=import-error,no-name-in-module
    from PIL import Image, ImageChops, ImageTk
    has_PIL = True
except ImportError:  # Some PIL installations live outside of the PIL package
    # pylint:disable=import-error,no-name-in-module
    try:
        import Image, ImageChops, ImageTk
        has_PIL = True
    except ImportError:  # No PIL compatible library
        has_PIL = False

has_PNG = has_PIL or (TkVersion >= 8.6)  # Tk 8.6 supports PNG natively

class GraphicsPreview(ChildWindow):
    """Graphics preview window."""
    def __init__(self, parent):
        self.colorscheme = None
        super(GraphicsPreview, self).__init__(parent, 'Graphics preview')
        self.top.resizable(0, 0)
        self.top.withdraw()
        self.top.protocol('WM_DELETE_WINDOW', self.top.withdraw)
        self.use_pack(paths.get('df'))

    def create_controls(self, container):
        if not has_PIL:
            Label(
                container,
                text="Preview requires a PIL-compatible library.").pack()
            return
        self.preview = Canvas(
            container, highlightthickness=0, takefocus=False, bg='black')
        self.preview.pack(fill=BOTH, expand=Y)

    @staticmethod
    def load_screenshot():
        """Loads screenshot data from a binary file."""
        f = open('screenshot.bin', 'rb')
        w = ord(f.read(1))
        h = ord(f.read(1))
        tiles = []
        for _ in range(0, h):
            row = []
            tiles.append(row)
            for _ in range(0, w):
                tile = ord(f.read(1))
                fg = ord(f.read(1))
                bg = ord(f.read(1))
                row.append([tile, fg, bg])
        f.close()
        return w, h, tiles

    @staticmethod
    def load_tileset(path):
        """Loads the tileset."""
        # pylint:disable=maybe-no-member
        return Image.open(path)

    @staticmethod
    def make_tile(tileset, char, fg, bg):
        """Returns an image objectof the tile, colored.

        Arguments:
            tileset:
                the Image object of the tileset to use
            ord_int:
                the ord integer of the character to use
            fg_c:
                a RGB color tuple for the tile foreground
            bg_c:
                a RGB color tuple for the tile background

        Returns:
            Image object of the tile
        """
        tile_x, tile_y = tuple(int(n/16) for n in tileset.size)
        x = tile_x * (char % 16)
        y = tile_y * (char // 16)
        tile = tileset.crop((x, y, x + tile_x, y + tile_y)).copy()
        tile_copy = tile.copy()
        tile.paste(bg, None)
        fg_tile = Image.new("RGBA", tile.size, fg) #pylint:disable=maybe-no-member
        tile_copy = ImageChops.multiply(tile_copy, fg_tile)
        tile.paste(tile_copy, None, tile_copy)
        return tile.convert("RGB")

    def get_draw_mode(self):
        """Returns a string identifying how to draw the preview."""
        init_raw = dfraw.DFRaw(os.path.join(
            self.path, 'data', 'init', 'init.txt'))
        if str(init_raw.get_value('PRINT_MODE')).startswith('TWBT'):
            return 'TWBT'
        gfx = init_raw.get_value('GRAPHICS')
        log.d(gfx)
        if gfx == 'YES':
            return 'GFXFONT'
        else:
            return 'FONT'

    def use_pack(self, path):
        """Loads tilesets from a pack located at <path>."""
        self.path = path
        init_raw = dfraw.DFRaw(os.path.join(path, 'data', 'init', 'init.txt'))
        font = init_raw.get_value('FONT')
        self.font = self.load_tileset(graphics.get_tileset_from_path(path, font))
        if lnp.settings.version_has_option('GRAPHICS_FONT'):
            gfx_font = init_raw.get_value('GRAPHICS_FONT')
            self.gfx_font = self.load_tileset(graphics.get_tileset_from_path(
                path, gfx_font))
        else:
            self.gfx_font = font
        self.draw()

    def use_font(self, tileset):
        """Loads FONT tileset from tileset named <tileset>."""
        self.font = self.load_tileset(paths.get('data', 'art', tileset))
        self.draw()

    def use_graphics_font(self, tileset):
        """Loads GRAPHICS_FONT tileset from tileset named <tileset>."""
        self.gfx_font = self.load_tileset(paths.get('data', 'art', tileset))
        self.draw()

    def use_colors(self, colorscheme, redraw=True):
        """Loads a colorscheme named <colorscheme>."""
        self.colorscheme = colorscheme
        if redraw:
            self.draw()

    @staticmethod
    def fix_tileset(tileset):
        """Transforms tilesets to RGBA."""
        log.d('Tileset mode is ' + tileset.mode)
        if tileset.mode == 'P':
            #tile_data = [255 if a != 0 else 0 for a in tileset.getdata()]
            #mask = Image.new("L", tileset.size) #pylint:disable=maybe-no-member
            #mask.putdata(tile_data)
            tileset = tileset.convert("RGB")
            #tileset.putalpha(mask)
        if tileset.mode == 'RGB':
            tileset = tileset.convert("RGBA")
            pixels = tileset.load()
            for y in range(tileset.size[1]):
                for x in range(tileset.size[0]):
                    if pixels[x, y] == (255, 0, 255, 255):
                        pixels[x, y] = (0, 0, 0, 0)
        else:
            tileset = tileset.convert("RGBA")
        return tileset

    def make_image(self):
        """Create the preview image object."""
        # pylint:disable=maybe-no-member
        c = colors.get_colors(self.colorscheme)
        w, h, tiles = self.load_screenshot()
        self.font = self.fix_tileset(self.font)
        self.gfx_font = self.fix_tileset(self.gfx_font)
        #TODO: TWBT
        tileset = (self.gfx_font if self.get_draw_mode() == 'GFXFONT' else
                   self.font)
        tile_x, tile_y = tuple(int(n/16) for n in tileset.size)
        preview = Image.new('RGBA', (tile_x * w, tile_y * h), None)
        for y, row in enumerate(tiles):
            for x, cell in enumerate(row):
                char, fg, bg = cell
                tile = self.make_tile(tileset, char, c[fg], c[bg])
                pos = (x * tile_x, y * tile_y)
                preview.paste(tile, pos)
        return preview

    def draw(self):
        """Draw a preview image."""
        from time import time
        start = time()
        image = self.make_image()
        self.preview.image = ImageTk.PhotoImage(image)
        self.top.geometry('{}x{}'.format(*image.size))
        self.preview.create_image(0, 0, image=self.preview.image, anchor=NW)
        end = time()
        log.d('Took '+str(end-start)+' seconds to draw preview')

# vim:expandtab
