import pytest

from pygears import Intf
from pygears.cookbook import alternate_queues, delay_rng
from pygears.cookbook.verif import directed
from pygears.sim import sim
from pygears.cookbook.verif import drv
from pygears.typing import Int, Queue, Uint
from pygears.util.test_utils import formal_check, synth_check


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_2_inputs(tmpdir, sim_cls, din_delay, dout_delay):
    t_din0 = Queue[Uint[8], 2]
    t_din1 = Queue[Int[8], 2]
    seq0 = [[list(range(8)), list(range(2))],
            [list(range(3)), list(range(1)),
             list(range(2))]]
    seq1 = [[list(range(1)),
             list(range(2)),
             list(range(3)),
             list(range(4))], [list(range(5))]]

    directed(
        drv(t=t_din0, seq=seq0) | delay_rng(din_delay, din_delay),
        drv(t=t_din1, seq=seq1) | delay_rng(din_delay, din_delay),
        f=alternate_queues(sim_cls=sim_cls),
        ref=[seq0, seq1],
        delays=[
            delay_rng(dout_delay, dout_delay),
            delay_rng(dout_delay, dout_delay)
        ])

    sim(outdir=tmpdir)


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_3_inputs(tmpdir, sim_cls, din_delay, dout_delay):
    din_num = 3

    t_din = Queue[Uint[8]]
    seq = []
    for _ in range(din_num):
        seq.append([list(range(4)), list(range(3)), list(range(2))])
    ref = seq

    directed(
        drv(t=t_din, seq=seq[0]) | delay_rng(din_delay, din_delay),
        drv(t=t_din, seq=seq[1]) | delay_rng(din_delay, din_delay),
        drv(t=t_din, seq=seq[2]) | delay_rng(din_delay, din_delay),
        f=alternate_queues(sim_cls=sim_cls),
        ref=ref,
        delays=[delay_rng(dout_delay, dout_delay)] * din_num)

    sim(outdir=tmpdir)


@formal_check(asserts={
    'dout0': 'dout0_data == din0_data',
    'dout1': 'dout1_data == din1_data'
})
def test_2_inputs_formal():
    alternate_queues(Intf(Queue[Uint[8], 2]), Intf(Queue[Uint[8], 2]))


@formal_check()
def test_multi_inputs():
    alternate_queues(
        Intf(Queue[Uint[8], 3]), Intf(Queue[Uint[8], 3]),
        Intf(Queue[Uint[8], 3]))


@synth_check({'logic luts': 4, 'ffs': 1})
def test_2_inputs_synth():
    alternate_queues(Intf(Queue[Uint[8], 2]), Intf(Queue[Uint[8], 2]))
