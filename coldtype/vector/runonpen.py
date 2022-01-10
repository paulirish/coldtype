from copy import deepcopy

from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.reverseContourPen import ReverseContourPen

from coldtype.geometry import Rect, Point, txt_to_edge
from coldtype.runon.runon import Runon

from coldtype.vector.mixins.FXMixin import FXMixin
from coldtype.vector.mixins.GlyphMixin import GlyphMixin
from coldtype.vector.mixins.LayoutMixin import LayoutMixin
from coldtype.vector.mixins.StylingMixin import StylingMixin
from coldtype.vector.mixins.DrawingMixin import DrawingMixin
from coldtype.vector.mixins.PathopsMixin import PathopsMixin
from coldtype.vector.mixins.ShorthandMixin import ShorthandMixin
from coldtype.vector.mixins.SegmentingMixin import SegmentingMixin
from coldtype.vector.mixins.SerializationMixin import SerializationMixin

class RunonPen(Runon,
    StylingMixin,
    LayoutMixin,
    DrawingMixin,
    PathopsMixin,
    SegmentingMixin,
    SerializationMixin,
    ShorthandMixin,
    GlyphMixin,
    FXMixin
    ):
    def FromPens(pens):
        if hasattr(pens, "_pens"):
            out = RunonPen().data(**pens.data)
            for p in pens:
                out.append(RunonPen.FromPens(p))
        elif hasattr(pens, "_els") and len(pens._els) > 0:
            out = pens
        elif hasattr(pens, "_val") and pens.val_present():
            out = pens
        else:
            p = pens
            rp = RecordingPen()
            p.replay(rp)
            out = RunonPen(rp)
            
            attrs = p.attrs.get("default", {})
            if "fill" in attrs:
                out.f(attrs["fill"])
            if "stroke" in attrs:
                out.s(attrs["stroke"]["color"])
                out.sw(attrs["stroke"]["weight"])

            # TODO also the rest of the styles

            out.data(**pens.data)

            if hasattr(pens, "_frame"):
                out.data(frame=pens._frame)
            if hasattr(pens, "glyphName"):
                out.data(glyphName=pens.glyphName)
        return out
    
    def __init__(self, *vals):        
        super().__init__(*vals)

        if isinstance(self._val, RecordingPen):
            pass
        elif isinstance(self._val, Rect):
            r = self._val
            self._val = RecordingPen()
            self.rect(r)
        else:
            raise Exception("Can’t understand _val", self._val)
        
        self._last = None
        ShorthandMixin.__init__(self)

    def reset_val(self):
        super().reset_val()
        self._val = RecordingPen()
        return self
    
    def val_present(self):
        return self._val and len(self._val.value) > 0
    
    def copy_val(self, val):
        copy = RecordingPen()
        copy.value = deepcopy(self._val.value)
        return copy
    
    def printable_val(self):
        if self.val_present():
            return f"{len(self._val.value)}mvs"
    
    def printable_data(self):
        out = {}
        exclude = ["_last_align_rect"]
        for k, v in self._data.items():
            if k not in exclude:
                out[k] = v
        return out

    def style(self, style="_default"):
        """for backwards compatibility with defaults and grouped-stroke-properties"""
        st = {**super().style(style)}
        return self.groupedStyle(st)
    
    def pen(self):
        """collapse and combine into a single vector"""
        if len(self) == 0:
            return self
        
        frame = self.ambit()
        self.collapse()

        for el in self._els:
            el._val.replay(self._val)
            #self._val.record(el._val)

        self._attrs = {**self._els[0]._attrs, **self._attrs}
            
        self.data(frame=frame)
        self._els = []
        return self
    
    def pens(self):
        if self.val_present():
            return self.ups()
        else:
            return self

    # multi-use overrides
    
    def reverse(self, recursive=False):
        """Reverse elements; if pen value present, reverse the winding direction of the pen."""
        if self.val_present():
            if self.unended():
                self.closePath()
            dp = RecordingPen()
            rp = ReverseContourPen(dp)
            self.replay(rp)
            self._val.value = dp.value
            return self

        return super().reverse(recursive=recursive)
    
    def index(self, idx, fn=None):
        if not self.val_present():
            return super().index(idx, fn)
        
        return self.mod_contour(idx, fn)
    
    def indices(self, idxs, fn=None):
        if not self.val_present():
            return super().indices(idxs, fn)

        def apply(idx, x, y):
            if idx in idxs:
                return fn(Point(x, y))
        
        return self.map_points(apply)
    
    def wordPens(self, pred=lambda x: x.glyphName == "space"):
        def _wp(p):
            return (p
                .split(pred)
                .map(lambda x: x
                    .data(word="/".join([p.glyphName for p in x]))
                    .pen()))
        
        d = self.depth()
        if d == 2:
            return _wp(self)
        
        out = type(self)()
        for pen in self:
            out.append(_wp(pen))
        return out
    
    def interpolate(self, value, other):
        if len(self.v.value) != len(other.v.value):
            raise Exception("Cannot interpolate / diff lens")
        vl = []
        for idx, (mv, pts) in enumerate(self.v.value):
            ipts = []
            for jdx, p in enumerate(pts):
                pta = Point(p)
                try:
                    ptb = Point(other.v.value[idx][-1][jdx])
                except IndexError:
                    print(">>>>>>>>>>>>> Can’t interpolate", idx, mv, "///", other.v.value[idx])
                    raise IndexError
                ipt = pta.interp(value, ptb)
                ipts.append(ipt)
            vl.append((mv, ipts))
        
        np = type(self)()
        np.v.value = vl
        return np
    
    def replaceGlyph(self, glyphName, replacement, limit=None):
        return self.replace(lambda p: p.glyphName == glyphName,
            lambda p: (replacement(p) if callable(replacement) else replacement)
                .translate(*p.ambit().xy()))
    
    def findGlyph(self, glyphName, fn=None):
        return self.find(lambda p: p.glyphName == glyphName, fn)
    
    def _repr_html_(self):
        if self.data("_notebook_shown"):
            return None
        
        from coldtype.notebook import show, DEFAULT_DISPLAY
        self.ch(show(DEFAULT_DISPLAY, th=1, tv=1))
        return None
    
    def text(self,
        text:str,
        style,
        frame:Rect,
        x="mnx",
        y="mny",
        ):
        self.rect(frame)
        self.data(
            text=text,
            style=style,
            align=(txt_to_edge(x), txt_to_edge(y)))
    
    # backwards compatibility

    def reversePens(self):
        """for backwards compatibility"""
        return self.reverse(recursive=False)
    
    rp = reversePens

    def vl(self, value):
        self.v.value = value
        return self

    @property
    def glyphName(self):
        return self.data("glyphName")
    
    def ffg(self, glyphName, fn=None, index=0):
        return self.find_({"glyphName":glyphName}, fn, index)
    
    @staticmethod
    def Enumerate(enumerable, enumerator):
        return RunonPen().enumerate(enumerable, enumerator)

def runonCast():
    def _runonCast(p):
        return RunonPen.FromPens(p)
    return _runonCast