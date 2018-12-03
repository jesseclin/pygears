from pygears import alternative, gear
from pygears.common import cart
from pygears.typing import Queue, Tuple, Uint


@gear(svgen={'compile': True})
async def take(din: Queue[Tuple['t_data', Uint]], *,
               init=1) -> Queue['t_data']:

    cnt = din.dtype[0][1](init)
    pass_eot = True

    async for ((data, size), eot) in din:
        last = (cnt == size) and pass_eot
        if (cnt <= size) and pass_eot:
            yield (data, eot or last)
        if last:
            pass_eot = 0
        cnt += 1


@alternative(take)
@gear
def take2(din: Queue['t_data'], cfg: Uint):
    return cart(din, cfg) | take


@alternative(take)
@gear(svgen={'svmod_fn': 'qtake.sv'})
async def qtake(din: Queue['Tdin', 2], cfg: Uint['N']) -> Queue['Tdin', 2]:
    '''
    Takes given number of queues. Number given by cfg.
    Counts lower eot. Higher eot resets.
    '''

    cnt = 0
    val = din.dtype((0, 0))

    async with cfg as c:
        while not all(val.eot):
            async with din as val:
                if cnt <= c:
                    yield din.dtype((val.data, val.eot[0], val.eot[1]
                                     or (cnt == (c - 1))))
                cnt += val.eot[0]
