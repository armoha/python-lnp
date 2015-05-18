#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint:disable=unused-wildcard-import,wildcard-import,invalid-name,attribute-defined-outside-init
"""Preview function for image sets."""
from __future__ import (
    print_function, unicode_literals, absolute_import, division)

import sys, os

from struct import Struct

from .child_windows import ChildWindow
from core import paths, colors, log, dfraw, graphics
from core.lnp import lnp
#pylint:disable=redefined-builtin
from io import open
from collections import namedtuple

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

Header = namedtuple('Header', ['w', 'h'])
Cell = namedtuple('Cell', ['char', 'fg', 'bg'])
TWBT_region = namedtuple('TWBT_region', ['x1', 'y1', 'x2', 'y2'])
Screen = namedtuple('Screen', ['header', 'tiles', 'twbt_region'])
header_fmt = Struct(str('<BB'))
cell_fmt = Struct(str('<BBB'))
TWBT_fmt = Struct(str('<BBBB'))

def unpack(strct, source):
    """Reads data using a Struct <strct> from <source>."""
    return strct.unpack(source.read(strct.size))

class GraphicsPreview(ChildWindow):
    #pylint:disable=too-many-instance-attributes
    """Graphics preview window."""
    def __init__(self, parent):
        self.print_mode = ''
        self.graphics = False
        super(GraphicsPreview, self).__init__(parent, 'Graphics preview')
        self.top.resizable(0, 0)
        self.top.withdraw()
        self.top.protocol('WM_DELETE_WINDOW', self.top.withdraw)
        self.load_screenshot()
        self.use_pack(paths.get('df'), None)

    def create_controls(self, container):
        if not has_PIL:
            Label(
                container,
                text="Preview requires a PIL-compatible library.").pack()
            return
        self.preview = Canvas(
            container, highlightthickness=0, takefocus=False, bg='black')
        self.preview.pack(fill=BOTH, expand=Y)

    def load_screenshot(self):
        """Loads screenshot data from a binary file."""
        f = open('screenshot.bin', 'rb')
        #pylint:disable=protected-access,no-member
        header = Header._make(unpack(header_fmt, f))
        tiles = []
        for _ in range(0, header.h):
            row = []
            for _ in range(0, header.w):
                row.append(Cell._make(unpack(cell_fmt, f)))
            tiles.append(row)
        twbt_region = TWBT_region._make(unpack(TWBT_fmt, f))
        f.close()
        self.screen = Screen(header, tiles, twbt_region)

    def load_tileset(self, path):
        """Loads the tileset."""
        # pylint:disable=maybe-no-member
        if not has_PIL:
            return None
        return self.fix_tileset(Image.open(path))

    def get_draw_mode(self):
        """Returns a string identifying how to draw the preview."""
        if self.print_mode.startswith('TWBT'):
            return self.print_mode
        if self.graphics:
            return 'GFXFONT'
        else:
            return 'FONT'

    def use_pack(self, path, colorscheme):
        """Loads tilesets from a pack located at <path>, with colorscheme at
        path <colorscheme>."""
        self.path = path
        self.colorscheme = colorscheme
        init_raw = dfraw.DFRaw(os.path.join(path, 'data', 'init', 'init.txt'))
        font = init_raw.get_value('FONT')
        self.font_name = graphics.get_tileset_from_path(path, font)
        self.font = self.load_tileset(self.font_name)
        if lnp.settings.version_has_option('GRAPHICS_FONT'):
            gfx_font = init_raw.get_value('GRAPHICS_FONT')
            self.gfx_font_name = graphics.get_tileset_from_path(path, gfx_font)
            self.gfx_font = self.load_tileset(self.gfx_font_name)
        else:
            self.gfx_font = font
        self.draw()

    def use_font(self, tileset):
        """Loads FONT tileset from tileset named <tileset>."""
        new_path = paths.get('data', 'art', tileset)
        if new_path == self.font_name:
            return
        self.font_name = new_path
        self.font = self.load_tileset(self.font_name)
        self.draw()

    def use_graphics_font(self, tileset):
        """Loads GRAPHICS_FONT tileset from tileset named <tileset>."""
        new_path = paths.get('data', 'art', tileset)
        if new_path == self.gfx_font_name:
            return
        self.gfx_font_name = new_path
        self.gfx_font = self.load_tileset(self.gfx_font_name)
        self.draw()

    def use_colors(self, colorscheme):
        """Loads a colorscheme named <colorscheme>."""
        if self.colorscheme == colorscheme:
            return
        self.colorscheme = colorscheme
        self.draw()

    def use_print_mode(self, print_mode):
        """Sets the print mode to <print_mode>."""
        old_draw_mode = self.get_draw_mode()
        self.print_mode = print_mode
        if old_draw_mode != self.get_draw_mode():
            self.draw()

    def change_graphics_option(self, value):
        """Callback when the GRAPHICS option is changed."""
        new_val = value == 'YES'
        if new_val != self.graphics:
            self.graphics = new_val
            self.draw()

    @staticmethod
    def fix_tileset(tileset):
        """Transforms tilesets to RGBA."""
        log.d('Tileset mode is ' + tileset.mode)
        if tileset.mode in ('P', 'RGB'):
            tileset = tileset.convert("RGBA")
            pixels = tileset.load()
            for y in range(tileset.size[1]):
                for x in range(tileset.size[0]):
                    if pixels[x, y] == (255, 0, 255, 255):
                        pixels[x, y] = (0, 0, 0, 0)
        else:
            tileset = tileset.convert("RGBA")
        return tileset

    def get_texture_filter(self):
        """Returns the PIL resampling filter matching DF's TEXTURE_PARAM."""
        init_raw = dfraw.DFRaw(os.path.join(
            self.path, 'data', 'init', 'init.txt'))
        if init_raw.get_value('TEXTURE_PARAM') == 'LINEAR':
            return Image.BILINEAR
        return Image.NEAREST

    def make_image(self, _region=None):
        """Create the preview image object. If provided, _region"""
        # pylint:disable=maybe-no-member,too-many-locals,no-member,too-many-branches
        c = colors.get_colors(self.colorscheme)
        screen = self.screen
        draw_mode = self.get_draw_mode()
        if _region or draw_mode == 'GFXFONT':
            tileset = self.gfx_font
        else:
            tileset = self.font
        tile_x, tile_y = tuple(int(n/16) for n in tileset.size)
        gfx_tile_x, gfx_tile_y = tuple(int(n/16) for n in self.gfx_font.size)
        img_size = (tile_x * screen.header.w, tile_y * screen.header.h)
        bg = Image.new('RGBA', img_size, (0, 0, 0, 255))
        tiles = Image.new('RGBA', img_size, (0, 0, 0, 255))
        fg = Image.new('RGBA', img_size, (0, 0, 0, 255))

        def tile_pos(char):
            """Calculates the pixel position of a tile in a tileset."""
            y, x = divmod(char, 16)
            return pos_in_pixels(x, y)

        def pos_in_pixels(x1, y1, x2=-1, y2=-1, gfx=False):
            """Convert tile coordinates (x,y) to pixel coordinates."""
            if x2 == -1:
                x2 = x1 + 1
            if y2 == -1:
                y2 = y1 + 1
            if gfx:
                tx, ty = gfx_tile_x, gfx_tile_y
            else:
                tx, ty = tile_x, tile_y
            return (x1 * tx, y1 * ty, x2 * tx, y2 * ty)

        for y, row in enumerate(screen.tiles):
            for x, cell in enumerate(row):
                if _region and not (
                        _region.x1 <= x <= _region.x2 and
                        _region.y1 <= y <= _region.y2):
                    continue
                pos = pos_in_pixels(x, y)
                tile = tileset.crop(tile_pos(cell.char))
                # The below code can be used to get entirely correct rendering,
                # but it takes way too long, so we make an approximation later.
                # if draw_mode == 'TWBT_LEGACY':
                #    tile = tile.resize(
                #        (gfx_tile_x, gfx_tile_y), self.get_texture_filter())
                #    pos = pos_in_pixels(x, y, graphics=True)
                tiles.paste(tile, pos)
                fg.paste(c[cell.fg], pos)
                bg.paste(c[cell.bg], pos)

        tiles = ImageChops.multiply(tiles, fg)
        bg.paste(tiles, mask=tiles)
        if draw_mode.startswith('TWBT') and not _region:
            twbt_img = self.make_image(screen.twbt_region)
            # To approximate TWBT_LEGACY rendering, FONT needs to be rescaled
            # to the same size as GRAPHICS_FONT. We can't afford to do that
            # with the individual tiles, so we approximate by rendering at
            # normal size and then scaling up at the end.
            if draw_mode == 'TWBT_LEGACY':
                bg = bg.resize(twbt_img.size, self.get_texture_filter())
            dest_pos = pos_in_pixels(
                *screen.twbt_region, gfx=(draw_mode == 'TWBT_LEGACY'))
            src_pos = list(pos_in_pixels(*screen.twbt_region, gfx=True))
            src_pos[2] = src_pos[0]+(dest_pos[2]-dest_pos[0])
            src_pos[3] = src_pos[1]+(dest_pos[3]-dest_pos[1])
            bg.paste(twbt_img.crop(src_pos), dest_pos)
        return bg

    def draw(self):
        """Draw a preview image."""
        if not has_PIL:
            return
        from time import time
        start = time()
        image = self.make_image()
        self.preview.image = ImageTk.PhotoImage(image)
        self.top.geometry('{}x{}'.format(*image.size))
        self.preview.create_image(0, 0, image=self.preview.image, anchor=NW)
        end = time()
        log.d('Took '+str(end-start)+' seconds to draw preview')

# vim:expandtab
