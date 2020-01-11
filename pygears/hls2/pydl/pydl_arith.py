import ast
from pygears.typing import Any, Fixpnumber, Tuple, Uint, Unit
from . import nodes as expr
from pygears.core.type_match import type_match, TypeMatchError


def tuple_mul_resolver(opexp, module_data):
    if not isinstance(opexp[1], expr.ResExpr):
        raise TypeMatchError

    return expr.ConcatExpr(opexp[0].operands * int(opexp[1].val))


def concat_resolver(opexp, module_data):
    ops = tuple(op for op in reversed(opexp) if int(op.dtype))

    if len(ops) == 0:
        return expr.ResExpr(Unit())
    elif len(ops) == 1:
        return ops[0]
    else:
        tuple_res = expr.ConcatExpr(ops)
        return expr.CastExpr(tuple_res, Uint[tuple_res.dtype.width])


def fixp_add_resolver(opexp, module_data):
    t_op1 = opexp[0].dtype
    t_op2 = opexp[1].dtype

    t_sum = t_op1 + t_op2
    t_cast = t_sum.base[t_sum.integer - 1, t_sum.width - 1]
    sh1 = t_sum.fract - t_op1.fract
    sh2 = t_sum.fract - t_op2.fract

    if sh1 or sh2:

        def fixp__add__(op1: t_op1, op2: t_op2) -> t_sum:
            return t_cast(op1) + t_cast(op2)

        return fixp__add__
    else:
        return expr.BinOpExpr(opexp, '+')


def fixp_sub_resolver(opexp, module_data):
    t_op1 = opexp[0].dtype
    t_op2 = opexp[1].dtype

    t_sum = t_op1 - t_op2
    t_cast = t_sum.base[t_sum.integer - 1, t_sum.width - 1]
    sh1 = t_sum.fract - t_op1.fract
    sh2 = t_sum.fract - t_op2.fract

    if sh1 or sh2:

        def fixp__sub__(op1: t_op1, op2: t_op2) -> t_sum:
            return t_cast(op1) - t_cast(op2)

        return fixp__sub__
    else:
        return expr.BinOpExpr(opexp, '-')


resolvers = {
    ast.MatMult: {
        Any: concat_resolver
    },
    ast.Mult: {
        Tuple: tuple_mul_resolver
    },
    ast.Add: {
        Fixpnumber: fixp_add_resolver
    },
    ast.Sub: {
        Fixpnumber: fixp_sub_resolver
    }
}


def resolve_arith_func(op, opexp, module_data):
    if type(op) in resolvers:
        op_resolvers = resolvers[type(op)]
        for templ in op_resolvers:
            try:
                try:
                    type_match(opexp[0].dtype, templ)
                except AttributeError:
                    breakpoint()

                return op_resolvers[templ](opexp, module_data)
            except TypeMatchError:
                continue

    operator = expr.OPMAP[type(op)]
    finexpr = expr.BinOpExpr((opexp[0], opexp[1]), operator)
    for opi in opexp[2:]:
        finexpr = expr.BinOpExpr((finexpr, opi), operator)

    return finexpr