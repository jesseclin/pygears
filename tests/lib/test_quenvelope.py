from pygears import Intf
from pygears.typing import Uint, Queue, Unit
from pygears.lib import quenvelope
from pygears.lib.verif import directed
from pygears.lib.verif import drv
from pygears.sim import sim


def test_skip():
    iout = quenvelope(Intf(Queue[Uint[1], 3]), lvl=2)

    assert iout.dtype == Queue[Unit, 2]


def test_skip_sim(sim_cls):
    seq = [[list(range(1))], [list(range(1)), list(range(2))],
           [list(range(1)), list(range(2)),
            list(range(3))]]

    ref = [[Unit()], [Unit(), Unit()], [Unit(), Unit(), Unit()]]

    directed(drv(t=Queue[Uint[2], 3], seq=[seq]),
             f=quenvelope(lvl=2, sim_cls=sim_cls),
             ref=[ref])

    sim()


def test_all_pass():
    iout = quenvelope(Intf(Queue[Uint[1], 2]), lvl=2)

    assert iout.dtype == Queue[Unit, 2]
