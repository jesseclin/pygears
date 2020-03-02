from .. import ir

from .inline import inline, inline_res
from .exit_cond import infer_exit_cond, infer_in_cond
from .dead_code import remove_dead_code
from .register import infer_registers
from .schedule import schedule
from .generators import handle_generators

__all__ = [
    'inline', 'inline_res', 'infer_exit_cond', 'remove_dead_code',
    'infer_registers', 'infer_in_cond'
]
