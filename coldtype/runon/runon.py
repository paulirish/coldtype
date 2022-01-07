from textwrap import wrap

from typing import Callable, Optional
from inspect import signature
from random import Random
from time import sleep
from copy import deepcopy
from collections.abc import Iterable
from collections import namedtuple

from coldtype.fx.chainable import Chainable


def _arg_count(fn):
    return len(signature(fn).parameters)

def _call_idx_fn(fn, idx, arg):
    ac = _arg_count(fn)
    if ac == 1:
        return fn(arg)
    else:
        return fn(idx, arg)


RunonEnumerable = namedtuple("RunonEnumerable", ["i", "el", "e", "len", "k"])


class RunonException(Exception):
    pass


class RunonNoData:
    pass


class Runon:
    def __init__(self, *val):
        els = []

        if len(val) == 1 and not isinstance(val[0], Runon):
            if isinstance(val[0], Iterable):
                els = val[0]
                value = None
            else:
                value = val[0]
        else:
            value = None
            els = []
            for v in val:
                if isinstance(v, Runon):
                    els.append(v)
                else:
                    els.append(type(self)(v))

        self._val = None
        self.reset_val()
        
        if value is not None:
            self._val = self.normalize_val(value)

        self._els = els
        
        self._visible = True
        self._alpha = 1

        self._attrs = {}
        self._data = {}
        self._parent = None
        self._tag = None

        self._tmp_attr_tag = None
    
    def post_init(self):
        """subclass hook"""
        pass

    # Value operations

    def update(self, val):
        if callable(val):
            val = val(self)
        
        self._val = val
        return self
    
    @property
    def v(self):
        return self._val

    # Array Operations

    def _norm_element(self, el):
        if el is None:
            return None
        
        if callable(el):
            el = el(self)
        if not isinstance(el, Runon):
            el = type(self)(el)
        return el

    def append(self, el):
        el = self._norm_element(el)
        if el is None:
            return self
        self._els.append(el)
        return self
    
    def extend(self, els):
        if callable(els):
            els = els(self)

        if isinstance(els, Runon):
            if len(els) > 0:
                self.append(els._els)
            else:
                self.append(els)
        else:
            [self.append(el) for el in els]
        return self
    
    def insert(self, idx, el):
        el = self._norm_element(el)
        
        if el is None:
            return self
        
        parent = self
        try:
            p = self
            for x in idx[:-1]:
                if len(self) > 0:
                    parent = p
                    p = p[x]
            
            p._els.insert(idx[-1], el)
            return self
        except TypeError:
            pass

        parent._els.insert(idx, el)
        return self
    
    def __iadd__(self, item):
        """alias to append"""
        return self.append(item)
    
    def __add__(self, item):
        """yields new Runon with current nested, item after"""
        return type(self)(self, item)
    
    # Generic Interface

    def __str__(self):
        return self.__repr__()
    
    def printable_val(self):
        """subclass hook for __repr__"""
        return self._val
    
    def printable_data(self):
        """subclass hook for __repr__"""
        return self._data
    
    def __repr__(self):
        v = self.printable_val()
        t = self._tag
        d = self.printable_data()
        l = len(self)

        if v is None:
            v = ""
        else:
            v = f"({v})"
        
        if l == 0:
            l = ""
        else:
            l = "/" + str(l) + "..."
        
        if t is None:
            t = ""
        else:
            t = f" {{#{t}}}"
        
        if len(d) == 0:
            d = ""
        else:
            d = " {" + ",".join([f"{k}={v}" for k,v in d.items()]) + "}"
        
        if self.val_present():
            tv = type(self._val).__name__
            if len(tv) > 5:
                tv = tv[:5] + "..."
        else:
            tv = ""
        
        ty = type(self).__name__
        if ty == "Runon":
            ty = ""
        
        out = f"<®:{ty}:{tv}{v}{l}{t}{d}>"
        return out
    
    def __bool__(self):
        return len(self._els) > 0 or self._val is not None
    
    def val_present(self):
        """subclass hook"""
        return bool(self._val)
    
    def normalize_val(self, val):
        """subclass hook"""
        return val
    
    def reset_val(self):
        self._val = None
        self._data = {}
        self._attrs = {}
        self._tag = None
        return self
    
    def __len__(self):
        return len(self._els)

    def __getitem__(self, index):
        #try:
        return self._els[index]
        #except IndexError:
        #    return None
        
    def __setitem__(self, index, pen):
        self._els[index] = pen
    
    def tree(self, v=True, limit=100):
        out = []
        def walker(el, pos, data):
            if pos <= 0:
                if pos == 0 and not v:
                    return
                
                dep = data.get("depth", 0)
                tab = " |"*dep
                if pos == 0:
                    tab = tab[:-1] + "-"
                
                sel = str(el)
                sel = wrap(sel, limit, initial_indent="", subsequent_indent="  "*(dep+2) + " ")
                out.append(tab + " " + "\n".join(sel))
        
        self.walk(walker)
        return "\n" + "\n".join(out)
    
    def depth(self):
        if len(self) > 0:
            return 1 + max(p.depth() for p in self)
        else:
            return 1
    
    # Iteration operations

    def walk(self,
        callback:Callable[["Runon", int, dict], None],
        depth=0,
        visible_only=False,
        parent=None,
        alpha=1,
        idx=None
        ):
        if visible_only and not self._visible:
            return
        
        if parent:
            self._parent = parent
        
        alpha = self._alpha * alpha
        
        if len(self) > 0:
            callback(self, -1, dict(depth=depth, alpha=alpha, idx=idx))
            for pidx, el in enumerate(self._els):
                idxs = [*idx] if idx else []
                idxs.append(pidx)
                el.walk(callback, depth=depth+1, visible_only=visible_only, parent=self, alpha=alpha, idx=idxs)
            utag = "_".join([str(i) for i in idx]) if idx else None
            callback(self, 1, dict(depth=depth, alpha=alpha, idx=idx, utag=utag))
        else:
            #print("PARENT", idx)
            utag = "_".join([str(i) for i in idx]) if idx else None
            res = callback(self, 0, dict(
                depth=depth, alpha=alpha, idx=idx, utag=utag))
            
            if res is not None:
                parent[idx[-1]] = res
        
        return self
    
    def parent(self):
        if self._parent:
            return self._parent
        else:
            print("no parent set")
            return None

    def map(self, fn):
        for idx, p in enumerate(self._els):
            res = _call_idx_fn(fn, idx, p)
            if res:
                self._els[idx] = res
        return self
    
    def filter(self, fn):
        to_delete = []
        for idx, p in enumerate(self._els):
            res = _call_idx_fn(fn, idx, p)
            if res == False:
                to_delete.append(idx)
        to_delete = sorted(to_delete, reverse=True)
        for idx in to_delete:
            del self._els[idx]
        return self
    
    def mapv(self, fn):
        idx = 0
        def walker(el, pos, _):
            nonlocal idx
            if pos != 0: return
            
            res = _call_idx_fn(fn, idx, el)
            idx += 1
            return res
        
        return self.walk(walker)
    
    def filterv(self, fn):
        idx = 0
        def walker(el, pos, data):
            nonlocal idx
            
            if pos == 0:
                res = _call_idx_fn(fn, idx, el)
                if not res:
                    el.data(_walk_delete=True)
                idx += 1
                return None
            elif pos == 1:
                el.filter(lambda p: not p.data("_walk_delete"))
        
        return self.walk(walker)
    
    def delete(self):
        self._els = []
        self.reset_val()
        return self
    
    def unblank(self):
        return self.filterv(lambda p: p.val_present())
    
    removeBlanks = unblank
    
    def interpose(self, el_or_fn):
        new_els = []
        for idx, el in enumerate(self._els):
            if idx > 0:
                if callable(el_or_fn):
                    new_els.append(el_or_fn(idx-1))
                else:
                    new_els.append(el_or_fn.copy())
            new_els.append(el)
        self._els = new_els
        return self
    
    def split(self, fn, split=0):
        out = type(self)()
        curr = type(self)()

        for el in self._els:
            do_split = False
            if callable(fn):
                do_split = fn(el)
            else:
                if el._val == fn:
                    do_split = True
            
            if do_split:
                if split == -1:
                    curr.append(el)
                out.append(curr)
                curr = type(self)()
                if split == 1:
                    curr.append(el)
            else:
                curr.append(el)
        
        out.append(curr)
        self._els = out._els
        return self
    
    def enumerate(self, enumerable, enumerator):
        if len(enumerable) == 0:
            return self
        
        es = list(enumerable)
        length = len(es)

        if isinstance(enumerable, dict):
            for idx, k in enumerate(enumerable.keys()):
                item = enumerable[k]
                if idx == 0 and len(enumerable) == 1:
                    e = 0.5
                else:
                    e = idx / (length-1)
                self.append(enumerator(RunonEnumerable(idx, item, e, length, k)))
        else:
            for idx, item in enumerate(es):
                if idx == 0 and len(enumerable) == 1:
                    e = 0.5
                else:
                    e = idx / (length-1)
                self.append(enumerator(RunonEnumerable(idx, item, e, length, idx)))
        return self
    
    # Hierarchical Operations

    def collapse(self):
        """AKA `flatten` in some programming contexts"""
        els = []
        def walk(el, pos, data):
            if pos == 0:
                els.append(el)
        
        self.walk(walk)
        self._els = els
        return self
    
    def sum(self):
        r = self.copy().collapse()
        out = []
        for el in r:
            out.append(el._val)
        return out
    
    def reverse(self, recursive=False):
        """in-place element reversal"""
        self._els = list(reversed(self._els))
        if recursive:
            for el in self._els:
                el.reverse(recursive=True)
        return self
    
    def shuffle(self, seed=0):
        "in-place shuffle"
        r = Random()
        r.seed(seed)
        r.shuffle(self._els)
        return self
    
    def copy_val(self, val):
        if hasattr(val, "copy"):
            return val.copy()
        else:
            return val
    
    def copy(self, deep=True, with_data=True):
        """with_data is deprecated"""
        val_copy = self.copy_val(self._val)

        _copy = type(self)(val_copy)
        copied = False
        
        if deep:
            try:
                _copy._data = deepcopy(self._data)
                _copy._attrs = deepcopy(self._attrs)
                copied = True
            except TypeError:
                pass
        
        if not copied:
            _copy._data = self._data.copy()
            _copy._attrs = self._attrs.copy()
        
        _copy._tag = self._tag
        
        for el in self._els:
            _copy.append(el.copy())
        
        return _copy
    
    def index(self, idx, fn=None):
        parent = self
        lidx = idx
        try:
            p = self
            for x in idx:
                if len(self) > 0:
                    parent = p
                    lidx = x
                    p = p[x]
                else:
                    return p.index(x, fn)
        except TypeError:
            p = self[idx]

        if fn:
            parent[lidx] = _call_idx_fn(fn, lidx, p)
        else:
            return parent[lidx]
        return self
    
    def indices(self, idxs, fn=None):
        out = []
        for idx in idxs:
            out.append(self.index(idx, fn))
        if fn is None:
            return out
        return self
    
    def î(self, idx, fn=None):
        return self.index(idx, fn)

    def ï(self, idxs, fn=None):
        return self.indices(idxs, fn)

    def find(self,
        finder_fn,
        fn=None,
        index=None
        ):
        matches = []
        def finder(p, pos, _):
            #if limit and len(matches) > limit:
            #    return

            found = False
            if pos >= 0:
                if isinstance(finder_fn, str):
                    found = p.tag() == finder_fn
                elif callable(finder_fn):
                    found = finder_fn(p)
                else:
                    found = all(p.data(k) == v for k, v in finder_fn.items())
            if found:
                matches.append(p)

        self.walk(finder)

        narrowed = []
        if index is not None:
            for idx, match in enumerate(matches):
                if isinstance(index, int):
                    if idx == index:
                        narrowed.append([idx, match])
                else:
                    if idx in index:
                        narrowed.append([idx, match])
        else:
            for idx, match in enumerate(matches):
                narrowed.append([idx, match])
        
        if fn:
            for idx, match in narrowed:
                _call_idx_fn(fn, idx, match)

        if fn:
            return self
        else:
            return [m for (_, m) in narrowed]
    
    def find_(self, finder_fn, fn=None, index=0):
        res = self.find(finder_fn, fn, index=index)
        if not fn:
            return res[0]
        else:
            return self
    
    # Data-access methods

    def data(self, key=None, default=None, **kwargs):
        if key is None and len(kwargs) > 0:
            for k, v in kwargs.items():
                if callable(v):
                    v = _call_idx_fn(v, k, self)
                self._data[k] = v
            return self
        elif key is not None:
            return self._data.get(key, default)
        else:
            return self
    
    def tag(self, value=RunonNoData()):
        if isinstance(value, RunonNoData):
            return self._tag
        else:
            self._tag = value
            return self

    def style(self, style="_default"):
        if style and style in self._attrs:
            return self._attrs[style]
        else:
            return self._attrs.get("_default", {})

    def attr(self,
        tag=None,
        field=None,
        recursive=True,
        **kwargs
        ):

        if field is None and len(kwargs) == 0:
            field = tag
            tag = None

        if tag is None:
            if self._tmp_attr_tag is not None:
                tag = self._tmp_attr_tag
            else:
                tag = "_default"
        
        if field: # getting, not setting
            return self._attrs.get(tag, {}).get(field)

        attrs = self._attrs.get(tag, {})
        for k, v in kwargs.items():
            attrs[k] = v
        
        self._attrs[tag] = attrs

        if recursive:
            for el in self._els:
                el.attr(tag=tag, field=None, recursive=True, **kwargs)
        
        return self
    
    def lattr(self, tag, fn):
        """temporarily change default tag to something other than 'default'"""
        self._tmp_attr_tag = tag
        fn(self)
        self._tmp_attr_tag = None
        return self
    
    def _get_set_prop(self, prop, v, castfn=None):
        if v is None:
            return getattr(self, prop)

        _v = v
        if callable(v):
            _v = v(self)
        
        if castfn is not None:
            _v = castfn(_v)

        setattr(self, prop, _v)
        return self
    
    def visible(self, v=None):
        return self._get_set_prop("_visible", v, bool)
    
    def alpha(self, v=None):
        return self._get_set_prop("_alpha", v, float)
    
    # Logic Operations

    def cond(self, condition,
        if_true:Callable[["Runon"], None], 
        if_false:Callable[["Runon"], None]=None
        ):
        if callable(condition):
            condition = condition(self)

        if condition:
            if callable(if_true):
                if_true(self)
            else:
                #self.gs(if_true)
                pass # TODO?
        else:
            if if_false is not None:
                if callable(if_false):
                    if_false(self)
                else:
                    #self.gs(if_false)
                    pass # TODO?
        return self
    
    # Chaining

    def chain(self,
        fn:Callable[["Runon"], None],
        *args
        ):
        """
        For simple take-one callback functions in a chain
        """
        if fn:
            if isinstance(fn, Chainable):
                res = fn.func(self, *args)
                if res:
                    return res
                return self
            
            try:
                if isinstance(fn[0], Chainable):
                    r = self
                    for f in fn:
                        r = r.chain(f, *args)
                    return r
            except TypeError:
                pass

            try:
                fn, metadata = fn
            except TypeError:
                metadata = {}
            
            # So you can pass in a function
            # without calling it (if it has no args)
            # TODO what happens w/ no args but kwargs?
            ac = _arg_count(fn)
            if ac == 0:
                fn = fn()

            res = fn(self, *args)
            if "returns" in metadata:
                return res
            elif isinstance(res, Runon):
                return res
            elif res:
                return res
        return self
    
    ch = chain

    def __or__(self, other):
        return self.chain(other)

    def __ror__(self, other):
        return self.chain(other)
    
    def __truediv__(self, other):
        return self.mapv(other)
    
    def __sub__(self, other):
        """noop"""
        return self

    def ups(self):
        copy = self.copy()

        self.reset_val()

        self._els = [copy]
        return self

    def layer(self, *layers):
        if len(layers) == 1 and isinstance(layers[0], int):
            layers = [1]*layers[0]
        
        els = []
        for layer in layers:
            if callable(layer):
                els.append(layer(self.copy()))
            elif isinstance(layer, Chainable):
                els.append(layer.func(self.copy()))
            else:
                els.append(self.copy())
        
        self.reset_val()
        self._els = els
        return self

    def layerv(self, *layers):
        if self.val_present():
            if len(layers) == 1 and isinstance(layers[0], int):
                layers = [1]*layers[0]
            
            els = []
            for layer in layers:
                if callable(layer):
                    els.append(layer(self.copy()))
                elif isinstance(layer, Chainable):
                    els.append(layer.func(self.copy()))
                else:
                    els.append(self.copy())
            
            self.reset_val()
            self.extend(els)
        else:
            for el in self._els:
                el.layerv(*layers)
        
        return self
    
    # Utils

    def print(self, *args):
        if len(args) == 0:
            print(self.tree())
            return self

        for a in args:
            if callable(a):
                print(a(self))
            else:
                print(a)
        return self
    
    def printh(self):
        """print hierarchy, no values"""
        print(self.tree(v=False))
        return self
    
    def noop(self, *args, **kwargs):
        """Does nothing"""
        return self
    
    def null(self):
        """For chaining; return an empty instead of this pen"""
        self.reset_val()
        self._els = []
        return self
    
    def _null(self):
        """For chaining; quickly disable a .null() call without a line-comment"""
        return self
    
    def sleep(self, time):
        """Sleep call within the chain (if you want to measure something)"""
        sleep(time)
        return self
    
    # Aliases

    pmap = mapv