from coldtype import *

@animation(timeline=120)
def simple(f):
    try:
        x, y = f.rec["cursor"].get(str(f.i))
    except:
        x, y = 0, 0
    
    out = P().enumerate(f.rec["cursor"], lambda x:
        P().oval(Rect.FromCenter(x.el, 30)).f(0 if x.i == 0 else hsl(x.i*0.01, 1, 0.8)))
    
    return P(
        #(P().rect(f.a.r.inset(f.e("eeio", r=(250, 500))))
        #    .f(hsl(0.65))),
        out,
        (P(Rect.FromCenter((x, y), 100)))
        )
