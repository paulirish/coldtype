import math, sys, os, re
from pathlib import Path

# source: https://github.com/PixarAnimationStudios/USD/issues/1372

def monkeypatch_ctypes():
    import ctypes.util, platform
    uname = os.uname()
    if uname.sysname == "Darwin" and uname.release >= "20.":
        real_find_library = ctypes.util.find_library
        def find_library(name):
            if name in {"OpenGL", "GLUT"}:  # add more names here if necessary
                return f"/System/Library/Frameworks/{name}.framework/{name}"
            elif name in {"freetype"}:
                res = real_find_library(name)
                if res.startswith("/usr/local") and platform.processor() == "arm":
                    return "/opt/homebrew/lib/libfreetype.dylib"
            return real_find_library(name)
        ctypes.util.find_library = find_library
    return

monkeypatch_ctypes()

from coldtype.text import *
from coldtype.text.reader import Font
from coldtype.pens.datpen import DATPen, DATPens, DATPenSet, DP, DPS, P, PS
from coldtype.pens.dattext import DATText
from coldtype.geometry import *
from coldtype.color import *
from coldtype.renderable import *
from coldtype.renderer.reader import Programs
from coldtype.helpers import loopidx, sibling, raw_ufo, ßhide, ßshow, cycle_idx, random_series, show_points, glyph_to_uni, uni_to_glyph, glyph_to_class, DefconFont
from coldtype.time import *
from coldtype.time.easing import ez
from coldtype.img.blendmode import BlendMode
from coldtype.grid import Grid

name = "coldtype"
__version__ = "0.7.7"

__FILE__ = None # will be redefined contextually
__sibling__ = lambda x: x # will be redefined contextually
__inputs__ = [] # will be redefined contextually
__memory__ = [] # will be redefined contextually
__as_config__ = False # will be redefined contextually
λ = None


def debug_txt(r, txt, font_size=42, **kwargs):
    return DATText(txt, Style("Times", font_size, load_font=0, **kwargs), r.inset(20))

def noop():
    return None