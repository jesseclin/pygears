import os

from nose import with_setup
from nose.tools import raises

from pygears import Intf, clear, bind, find, registry, MultiAlternativeError
from pygears.typing import Queue, Tuple, Uint, Int
from pygears.cookbook.rng import rng
from pygears.svgen.generate import svgen_module
from pygears.svgen import svgen
from utils import prepare_result_dir, svgen_test


@with_setup(clear)
def test_basic_unsigned():
    iout = rng(Intf(Tuple[Uint[4], Uint[2], Uint[2]]))

    rng_gear = find('/rng/sv_rng')

    assert iout.dtype == Queue[Uint[4]]
    assert not rng_gear.params['signed']


@with_setup(clear)
def test_basic_signed():
    iout = rng(Intf(Tuple[Int[4], Int[6], Uint[2]]))

    rng_gear = find('/rng/sv_rng')

    assert iout.dtype == Queue[Int[6]]
    assert rng_gear.params['signed']


@with_setup(clear)
def test_supply_constant():
    iout = rng((Uint[4](0), 8, 1))

    rng_gear = find('/rng/sv_rng')

    assert iout.dtype == Queue[Uint[4]]
    assert rng_gear.params['cfg'] == Tuple[Uint[4], Uint[4], Uint[1]]
    assert not rng_gear.params['signed']


@with_setup(clear)
def test_cnt_only():
    iout = rng(8)

    assert iout.dtype == Queue[Uint[4]]

    rng_gear = find('/rng/rng/sv_rng')
    assert rng_gear.params['cfg'] == Tuple[Uint[1], Uint[4], Uint[1]]


@with_setup(clear)
def test_cnt_down():
    iout = rng((7, 0, -1))

    rng_gear = find('/rng/sv_rng')

    assert rng_gear.params['signed']
    assert rng_gear.params['cfg'] == Tuple[Int[4], Int[2], Int[1]]
    assert iout.dtype == Queue[Int[4]]


@raises(MultiAlternativeError)
@with_setup(clear)
def test_multi_lvl():
    iout = rng((1, 2, 3), lvl=2)
    print(iout.dtype)


# bind('ErrReportLevel', 0)
# test_multi_lvl()


@with_setup(clear)
@svgen_test(['rng_hier.sv'])
def test_basic_unsigned_svgen():
    rng(Intf(Tuple[Uint[4], Uint[2], Uint[2]]))


@with_setup(clear)
@svgen_test(['rng_rng.sv', 'ccat.sv', 'rng_hier.sv'])
def test_cnt_svgen():
    rng(8)

# bind('ErrReportLevel', 0)
# test_basic_unsigned_svgen()

# def proba(din, *, dout, bla=2, **kwargs):
#     print("Here")
#     print(kwargs)


# def probac(din, *, dout, bla=2, **kwargs):
#     print(kwargs)


# from funcutils import FunctionBuilder
# fb = FunctionBuilder.from_func(proba)
# fb.kwonlyargs.append('proba1')
# # fb.body = 'proba(din, dout=dout, bla=bla, proba1=proba1)'
# # fb.body = 'probac(din, dout=dout, bla=bla, proba1=proba1)'
# # fb.body = 'print(globals())'
# fb.varkw = None
# f = fb.get_func()
# f(1, dout=2, proba1=7)
# print(f.__name__)

# from pygears.core.partial import argspec_unwrap
# ret = argspec_unwrap(f)
# print(ret.kwonlyargs)