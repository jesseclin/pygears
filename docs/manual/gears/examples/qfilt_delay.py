from pygears import datagear
from pygears.lib import filt, drv, check
from pygears.typing import Queue, Uint, Bool


@datagear
def even(x: Uint) -> Bool:
    return not x[0]


drv(t=Queue[Uint[8]], seq=[[0, 1, 3, 5, 7, 9]]) \
    | filt(f=even) \
    | check(ref=[[0]])
