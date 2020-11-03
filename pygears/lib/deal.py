from pygears import gear, alternative
from pygears.typing import Queue, Uint, Union, bitw
from .rng import qrange
from .flatten import flatten
from .ccat import ccat
from .demux import demux


@gear(hdl={'compile': True}, enablement=b'lvl < din.lvl')
async def qdeal(din: Queue, *, num,
                lvl=b'din.lvl-1') -> b'(Queue[din.data, din.lvl-1], ) * num':

    i = Uint[bitw(num)](0)

    async for (data, eot) in din:
        out_eot = eot[:lvl]

        dout = data if lvl == 0 else (data, out_eot)

        yield demux(i,
                    dout,
                    use_dflt=False,
                    mapping={n: n
                             for n in range(num)})

        if all(out_eot):
            if i == (num - 1):
                i = 0
            else:
                i += 1


@gear(hdl={'compile': True})
async def qdeal_same_lvl_impl(din: Queue, *, num,
                              lvl=b'din.lvl-1') -> b'Union[(din, ) * num]':

    i = Uint[bitw(num)](0)

    while i != num:
        async for (data, eot) in din:
            d = data if lvl == 0 else (data, eot)

            yield (d, i)

        i += 1

@alternative(qdeal)
@gear(enablement=b'lvl == din.lvl')
def qdeal_same_lvl(din: Queue, *, num,
                         lvl=b'din.lvl-1'):
    return din \
        | qdeal_same_lvl_impl(num=num, lvl=lvl) \
        | demux(use_dflt=False,
                mapping={n: n
                         for n in range(num)})


@gear
def deal(din, *, num) -> b'(din, ) * num':
    return ccat(din, qrange(num - 1, inclusive=True) | flatten) \
        | Union \
        | demux(use_dflt=False, mapping={i: i for i in range(num)})
