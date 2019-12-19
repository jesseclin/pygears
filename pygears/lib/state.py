from pygears import gear, alternative
from pygears.typing import Unit
from .const import ping


@gear(svgen={'node_cls': None})
async def state_din(din, *, init) -> None:
    pass


@gear(svgen={'node_cls': None})
async def state_dout(*, t) -> b't':
    pass


@gear(enablement=b'len(rd) > 0')
def state(din, *rd: Unit, init=0) -> b'(din,)*len(rd)':
    din | state_din(init=init)
    return tuple(state_dout(t=din.dtype) for _ in rd)


@alternative(state)
@gear
def state_perp(din, *, init=0):
    return state(din, ping(1))
