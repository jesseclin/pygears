from pygears import gear
from math import ceil, floor
from pygears.sim import sim
from pygears.typing import Fixp, Ufixp, Int
from pygears.lib import directed, drv


def test_abs():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[5, 9]:
        async with a_i as a, b_i as b:
            yield abs(a)
            yield abs(b)

    directed(drv(t=Ufixp[3, 6], seq=[7.875]),
             drv(t=Fixp[4, 8], seq=[-8.0]),
             f=test(__sim__='verilator'),
             ref=[7.875, 8.0])

    sim()


def test_add_bin():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[5, 9]:
        async with a_i as a, b_i as b:
            yield a + b
            yield b + a
            yield a + a
            yield b + b
            yield a + 2
            yield 2 + a
            yield b + 2
            yield 2 + b

    directed(drv(t=Ufixp[3, 6], seq=[7.875]),
             drv(t=Fixp[4, 8], seq=[-8.0]),
             f=test(__sim__='verilator'),
             ref=[-0.125, -0.125, 15.75, -16.0, 9.875, 9.875, -6, -6])

    sim(timeout=8)


def test_ceil():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[5, 9]:
        async with a_i as a, b_i as b:
            yield ceil(a)
            yield ceil(b)

    directed(drv(t=Ufixp[3, 6], seq=[7.875, 7.375]),
             drv(t=Fixp[4, 8], seq=[-8.0, -7.5]),
             f=test(__sim__='verilator'),
             ref=[8, -8, 8, -7])

    sim()


def test_floor():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[4, 8]:
        async with a_i as a, b_i as b:
            yield floor(a)
            yield floor(b)

    directed(drv(t=Ufixp[3, 6], seq=[7.875, 7.375]),
             drv(t=Fixp[4, 8], seq=[-8.0, -7.5]),
             f=test(__sim__='verilator'),
             ref=[7, -8, 7, -8])

    sim()


# def test_int():
#     @gear(hdl={'compile': True})
#     async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[4, 8]:
#         async with a_i as a, b_i as b:
#             yield int(a)
#             yield int(b)

#     directed(drv(t=Ufixp[3, 6], seq=[7.875, 7.375]),
#              drv(t=Fixp[4, 8], seq=[-8.0, -7.5]),
#              f=test(__sim__='verilator'),
#              ref=[7, -8, 7, -8])

#     sim()


def test_mul_bin():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[8, 16]:
        async with a_i as a, b_i as b:
            yield a * b
            yield b * a
            yield a * a
            yield b * b
            yield a * 2
            yield 2 * a
            yield b * 2
            yield 2 * b

    directed(drv(t=Ufixp[3, 6], seq=[7.875]),
             drv(t=Fixp[4, 8], seq=[-8.0]),
             f=test(__sim__='verilator'),
             ref=[-63.0, -63.0, 62.015625, 64.0, 15.75, 15.75, -16, -16])

    sim(timeout=8)


def test_sub_bin():
    @gear(hdl={'compile': True})
    async def test(a_i: Ufixp[3, 6], b_i: Fixp[4, 8]) -> Fixp[5, 9]:
        async with a_i as a, b_i as b:
            yield a - b
            yield b - a
            yield a - a
            yield b - b
            yield a - 2
            yield 2 - a
            yield b - 2
            yield 2 - b

    directed(drv(t=Ufixp[3, 6], seq=[7.875]),
             drv(t=Fixp[4, 8], seq=[-8.0]),
             f=test(__sim__='verilator'),
             ref=[15.875, -15.875, 0, 0, 5.875, -5.875, -10, 10])

    sim(timeout=8)
