from coldtype.pens.datpen import DATPen
from coldtype.geometry.rect import Rect
from coldtype.color import hsl


def cubicBezier(x1, y1, x2, y2):
    p = DATPen()
    p.moveTo((0, 0))
    p.curveTo((x1*1000, y1*1000), (x2*1000, y2*1000), (1000, 1000))
    p.endPath()
    p.addFrame(Rect(1000, 1000))
    return p.fssw(-1, hsl(0.6), 2)