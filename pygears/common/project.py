from pygears import gear
from pygears.typing import Queue


@gear(svgen={'svmod_fn': 'project.sv'})
async def project(din: Queue['tdin', 'din_lvl'],
                  *,
                  lvl=1,
                  dout_lvl=b'din_lvl - lvl') -> Queue['tdin', 'dout_lvl']:
    async with din as d:
        yield d.sub(lvl)
