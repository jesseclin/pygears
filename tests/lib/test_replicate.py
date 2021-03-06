import pytest

from pygears import Intf
from pygears.lib.delay import delay_rng
from pygears.lib.replicate import replicate, replicate_while
from pygears.lib.verif import directed, drv, verif
from pygears.sim import sim
from pygears.typing import Tuple, Uint, Bool, Queue
from pygears.util.test_utils import get_decoupled_dut, synth_check

SEQUENCE = [(2, 3), (5, 5), (3, 9), (8, 1)]
REF = list([x[1]] * x[0] for x in SEQUENCE)

T_DIN = Tuple[Uint[16], Uint[16]]


def test_directed(sim_cls):
    directed(drv(t=T_DIN, seq=SEQUENCE), f=replicate(sim_cls=sim_cls), ref=REF)
    sim()


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_directed_cosim(cosim_cls, din_delay, dout_delay):
    dut = get_decoupled_dut(dout_delay, replicate)
    verif(drv(t=T_DIN, seq=SEQUENCE) | delay_rng(din_delay, din_delay),
          f=dut(sim_cls=cosim_cls),
          ref=replicate(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim()


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_replicate_while(cosim_cls, din_delay, dout_delay):
    dut = get_decoupled_dut(dout_delay, replicate_while)
    verif(drv(t=Bool, seq=[1, 1, 0] * 5),
          drv(t=Uint[16], seq=list(range(5)))
          | delay_rng(din_delay, din_delay),
          f=dut(sim_cls=cosim_cls),
          ref=replicate_while(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim()


@pytest.mark.parametrize('din_delay', [0, 5])
@pytest.mark.parametrize('dout_delay', [0, 5])
def test_replicate_queue(cosim_cls, din_delay, dout_delay):
    dut = get_decoupled_dut(dout_delay, replicate_while)
    verif(drv(t=Bool, seq=[1, 1, 0] * 5),
          drv(t=Queue[Uint[16]], seq=[list(range(5))])
          | delay_rng(din_delay, din_delay),
          f=dut(sim_cls=cosim_cls),
          ref=replicate_while(name='ref_model'),
          delays=[delay_rng(dout_delay, dout_delay)])

    sim()


# from pygears.sim.modules import SimVerilated
# test_replicate_queue('/tools/home/tmp/replicate_while', SimVerilated, 0, 0)

# TODO: live fails
# @formal_check()
# def test_formal():
#     replicate(Intf(T_DIN))


@synth_check({'logic luts': 10, 'ffs': 16}, tool='vivado')
def test_synth_vivado():
    replicate(Intf(T_DIN))


@synth_check({'logic luts': 12, 'ffs': 16}, tool='yosys')
def test_synth_yosys():
    replicate(Intf(T_DIN))
