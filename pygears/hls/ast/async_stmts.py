import ast
from . import Context, ir, node_visitor, visit_ast
from .cast import resolve_cast_func
from .utils import add_to_list
from .stmt import assign_targets


def is_target_id(node):
    return isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)


# TODO: Revisit cast_return, maybe it can be more general
from pygears.typing import typeof, Queue, Tuple, Array


def cast_return(arg_nodes, out_ports):
    out_num = len(out_ports)
    if isinstance(arg_nodes, (list, tuple)):
        assert len(arg_nodes) == out_num
        input_vars = arg_nodes
    elif isinstance(arg_nodes, ir.Name) and out_num > 1:
        var = arg_nodes.obj
        assert len(var.dtype) == out_num
        input_vars = []
        for i in range(len(var.dtype)):
            input_vars.append(
                ir.SubscriptExpr(val=arg_nodes, index=ir.ResExpr(i)))
    else:
        assert out_num == 1
        input_vars = [arg_nodes]

    args = []
    for arg, intf in zip(input_vars, out_ports):
        port_t = intf.dtype
        if typeof(port_t, (Queue, Tuple, Array)):
            if isinstance(arg, ir.ConcatExpr) and arg.dtype != port_t:
                for i in range(len(arg.operands)):
                    if isinstance(arg.operands[i], ir.CastExpr) and (
                            arg.operands[i].cast_to == port_t[i]):
                        pass
                    else:
                        arg.operands[i] = resolve_cast_func(
                            arg.operands[i], port_t[i])

            args.append(arg)
        else:
            if arg.dtype != port_t:
                args.append(resolve_cast_func(arg, port_t))
            else:
                args.append(arg)

    return ir.TupleExpr(args)


@node_visitor(ast.Yield)
def parse_yield(node, ctx):
    yield_expr = visit_ast(node.value, ctx)

    try:
        ret = cast_return(yield_expr, ctx.gear.out_ports)
    except TypeError as e:
        breakpoint()
        raise TypeError(
            f"{str(e)}\n    - when casting output value to the output type")

    return [
        ir.AssignValue(ctx.out_ports[0], yield_expr),
        ir.ExprStatement(
            ir.Await(exit_await=ir.Component(ctx.out_ports[0], 'ready')))
    ]

    # return ir.Statement(exit_await=ir.Component(ctx.out_ports[0], 'ready'),
    #                     stmts=[ir.AssignValue(ctx.out_ports[0], yield_expr)])

    # return ir.Yield(ret, ports=ctx.out_ports)


@node_visitor(ast.withitem)
def withitem(node: ast.withitem, ctx: Context):
    # assert isinstance(ctx.pydl_parent_block, ir.IntfBlock)

    intf = visit_ast(node.context_expr, ctx)
    targets = visit_ast(node.optional_vars, ctx)

    if isinstance(intf, ir.ConcatExpr):
        data = ir.ConcatExpr([
            ir.Await(ir.Component(i, 'data'),
                     in_await=ir.Component(i, 'valid')) for i in intf.operands
        ])
    else:
        data = ir.Await(ir.Component(intf, 'data'),
                        in_await=ir.Component(intf, 'valid'))

    ass_targets = assign_targets(ctx, targets, data, ir.Variable)

    return intf, ass_targets


@node_visitor(ast.AsyncWith)
def asyncwith(node, ctx: Context):
    assigns = [visit_ast(i, ctx) for i in node.items]

    intfs = []
    stmts = []
    for intf, targets in assigns:
        if isinstance(intf, ir.ConcatExpr):
            intfs.extend(intf.operands)
        else:
            intfs.append(intf)

        add_to_list(stmts, targets)

    # ir_node = ir.IntfBlock(stmts=stmts, intfs=intfs)

    # ctx.pydl_block_closure.append(ir_node)

    # stmts = []

    for stmt in node.body:
        res_stmt = visit_ast(stmt, ctx)
        add_to_list(stmts, res_stmt)

    # ctx.pydl_block_closure.pop()

    # ir_node.close()

    for i in intfs:
        stmts.append(ir.AssignValue(ir.Component(i, 'ready'), ir.res_true))

    return stmts


class AsyncForContext:
    def __init__(self, intf, ctx):
        self.intf = intf
        self.ctx = ctx

    def __enter__(self):
        eot_name = self.ctx.find_unique_name('_eot')
        data_name = self.ctx.find_unique_name('_data')

        intf_obj = self.intf.obj.val

        self.ctx.scope[eot_name] = ir.Variable(eot_name, intf_obj.dtype.eot)
        self.ctx.scope[data_name] = ir.Variable(data_name, intf_obj.dtype.data)

        eot_init = ir.AssignValue(
            self.ctx.ref(eot_name),
            ir.ResExpr(intf_obj.dtype.eot(0)),
        )

        eot_test = ir.BinOpExpr(
            (self.ctx.ref(eot_name), ir.ResExpr(intf_obj.dtype.eot.max)),
            ir.opc.NotEq)

        eot_load = ir.AssignValue(
            self.ctx.ref(eot_name),
            ir.SubscriptExpr(ir.Component(self.intf, 'data'), ir.ResExpr(-1)))

        data_load = ir.AssignValue(
            self.ctx.ref(data_name),
            ir.Await(ir.Component(self.intf, 'data'),
                     in_await=ir.Component(self.intf, 'valid')))

        # intf_block = ir.IntfBlock(intfs=[self.intf], stmts=[eot_load])

        eot_loop_stmt = ir.LoopBlock(test=eot_test,
                                     stmts=[data_load, eot_load])

        self.ctx.pydl_block_closure.append(eot_loop_stmt)
        # self.ctx.pydl_block_closure.append(intf_block)

        # self.intf_block = intf_block

        return [eot_init, eot_loop_stmt]

    def __exit__(self, exception_type, exception_value, traceback):
        loop = self.ctx.pydl_block_closure.pop()
        loop.stmts.append(
            ir.AssignValue(ir.Component(self.intf, 'ready'), ir.res_true))


@node_visitor(ast.AsyncFor)
def AsyncFor(node, ctx: Context):
    out_intf_ref = visit_ast(node.iter, ctx)
    targets = visit_ast(node.target, ctx)

    with AsyncForContext(out_intf_ref, ctx) as stmts:
        add_to_list(
            ctx.pydl_parent_block.stmts,
            assign_targets(ctx, targets, ir.Component(out_intf_ref, 'data'),
                           ir.Variable))

        for stmt in node.body:
            res_stmt = visit_ast(stmt, ctx)
            add_to_list(ctx.pydl_parent_block.stmts, res_stmt)

        return stmts


@node_visitor(ast.Await)
def _(node: ast.Await, ctx: Context):
    return ir.ExprStatement(
        ir.Await(in_await=ir.res_false, exit_await=ir.res_false))