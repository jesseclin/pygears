import ast
import importlib

import hdl_types as ht
from pygears.typing import (Array, Int, Integer, Queue, Tuple, Uint, Unit,
                            bitw, is_type, typeof, Bool)
from pygears.typing.base import TypingMeta

opmap = {
    ast.Add: '+',
    ast.Sub: '-',
    ast.Mult: '*',
    ast.Div: '/',
    ast.Mod: '%',
    ast.Pow: '**',
    ast.LShift: '<<',
    ast.RShift: '>>>',
    ast.BitOr: '|',
    ast.BitAnd: '&',
    ast.BitXor: '^',
    ast.FloorDiv: '/',
    ast.Invert: '~',
    ast.Not: '!',
    ast.UAdd: '+',
    ast.USub: '-',
    ast.Eq: '==',
    ast.Gt: '>',
    ast.GtE: '>=',
    ast.Lt: '<',
    ast.LtE: '<=',
    ast.NotEq: '!=',
    ast.And: '&&',
    ast.Or: '||',
}


class VisitError(Exception):
    pass


class DeprecatedError(Exception):
    pass


class AstTypeError(Exception):
    pass


def set_pg_type(ret):
    if ret is None:
        return ret

    if isinstance(ret, (list, tuple)):
        for i, r in enumerate(ret):
            ret[i] = set_pg_type(r)
        return ret

    if not is_type(type(ret)):
        if ret < 0:
            ret = Int(ret)
        else:
            ret = Uint(ret)

    return ret


def eval_expression(node, local_namespace):
    return eval(
        compile(
            ast.Expression(ast.fix_missing_locations(node)),
            filename="<ast>",
            mode="eval"), local_namespace, globals())


def eval_data_expr(node, local_namespace):
    ret = eval_expression(node, local_namespace)

    if isinstance(ret, ast.AST):
        raise AstTypeError

    ret = set_pg_type(ret)

    return ht.ResExpr(ret)


def gather_control_stmt_vars(variables, intf, attr=None, dtype=None):
    if dtype is None:
        dtype = intf.intf.dtype
    if attr is None:
        attr = []
    else:
        for a in attr:
            dtype = dtype[a]

    scope = {}
    if isinstance(variables, ast.Tuple):
        for i, v in enumerate(variables.elts):
            if isinstance(v, ast.Name):
                scope[v.id] = ht.AttrExpr(intf, attr + [dtype.fields[i]])
            elif isinstance(v, ast.Starred):
                scope[v.id] = ht.AttrExpr(intf, attr + [dtype.fields[i]])
            elif isinstance(v, ast.Tuple):
                scope.update(
                    gather_control_stmt_vars(v, intf,
                                             attr + [dtype.fields[i]]))
    else:
        if isinstance(intf, ht.IntfExpr):
            scope[variables.id] = intf
        else:
            raise DeprecatedError

    return scope


class HdlAst(ast.NodeVisitor):
    def __init__(self, gear, regs, variables, intfs, call_paths):
        self.in_ports = [ht.IntfExpr(p) for p in gear.in_ports]
        self.out_ports = [ht.IntfExpr(p) for p in gear.out_ports]

        self.locals = {
            **intfs['namedargs'],
            **gear.explicit_params,
            **intfs['varargs']
        }
        self.variables = variables
        self.regs = regs
        self.in_intfs = intfs['vars']
        self.out_intfs = intfs['outputs']
        self.scope = []
        self.stage_hier = []

        named = {}
        for p in self.in_ports:
            if p.name in intfs['namedargs']:
                named[p.name] = p
        self.hdl_locals = {**named, **intfs['varargs']}

        self.gear = gear

        self.call_modules = []
        for path in call_paths:
            spec = importlib.util.spec_from_file_location('*', path)
            foo = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(foo)
            self.call_modules.append(foo)

    def enter_block(self, block):
        self.scope.append(block)

    def exit_block(self):
        self.scope.pop()

    def get_context_var(self, pyname):
        var = self.hdl_locals.get(pyname, None)

        if isinstance(var, ht.RegDef):
            if var.name in self.regs:
                return ht.OperandVal(var, 'reg')
            else:
                return ht.OperandVal(var, 's')
        elif isinstance(var, ht.VariableDef):
            return ht.OperandVal(var, 'v')
        elif isinstance(var, ht.IntfDef):
            return ht.OperandVal(var.intf, 's')

        return var

    def visit_block(self, svnode, body):

        self.enter_block(svnode)

        for stmt in body:
            svstmt = self.visit(stmt)
            if svstmt is not None:
                svnode.stmts.append(svstmt)

        self.exit_block()

        return svnode

    def intf_parse(self, intf, node, target):
        if isinstance(intf, ht.IntfDef):
            scope = gather_control_stmt_vars(
                node.target, intf, dtype=intf.intf[0].dtype)
            block_intf = ht.IntfDef(
                intf=intf.intf, name=intf.name, context='valid')
        else:
            block_intf = ht.IntfExpr(intf=intf.intf, context='valid')
            scope = gather_control_stmt_vars(target, intf)

        return scope, block_intf

    def visit_AsyncFor(self, node):
        intf = self.visit_NameExpression(node.iter)
        scope, loop_intf = self.intf_parse(
            intf=intf, node=node, target=node.target)

        self.hdl_locals.update(scope)

        hdl_node = ht.IntfLoop(intf=loop_intf, stmts=[], multicycle=scope)

        return self.visit_block(hdl_node, node.body)

    def visit_AsyncWith(self, node):
        header = node.items[0]

        intf = self.visit_NameExpression(header.context_expr)
        scope, block_intf = self.intf_parse(
            intf=intf, node=node, target=node.items[0].optional_vars)

        self.hdl_locals.update(scope)

        hdl_node = ht.IntfBlock(intf=block_intf, stmts=[])

        return self.visit_block(hdl_node, node.body)

    def visit_Subscript(self, node):
        val_expr = self.visit(node.value)

        if hasattr(node.slice, 'value'):
            data_index = False
            if isinstance(val_expr, ht.OperandVal) and (len(val_expr.op) > 1):
                data_index = True
            else:
                data_index = typeof(val_expr.dtype, (Array, Integer))

            if data_index:
                index = self.visit_DataExpression(node.slice.value)
                if isinstance(index, ht.ResExpr):
                    index = int(index.val)
            else:
                index = self.eval_expression(node.slice.value)
        else:
            slice_args = [
                self.eval_expression(getattr(node.slice, field))
                for field in ['lower', 'upper'] if getattr(node.slice, field)
            ]

            index = slice(*tuple(arg for arg in slice_args))
            if index.start is None:
                index = slice(0, index.stop, index.step)

        if hasattr(node.value, 'id') and node.value.id in self.out_intfs:
            # conditional assginment, not subscript
            for i, op in enumerate(val_expr.op):
                self.out_ports[i].context = ht.BinOpExpr(
                    (index, ht.ResExpr(i)), '==')
            return None
        else:
            hdl_node = ht.SubscriptExpr(val_expr, index)

        if hdl_node.dtype is Unit:
            return ht.ResExpr(Unit())
        else:
            return hdl_node

    def visit_Name(self, node):
        return self.get_context_var(node.id)

    def visit_Num(self, node):
        if node.n < 0:
            dtype = type(Int(node.n))
        else:
            dtype = type(Uint(node.n))

        return dtype, node.n

    def visit_AugAssign(self, node):
        target_load = ast.Name(node.target.id, ast.Load())
        expr = ast.BinOp(target_load, node.op, node.value)
        assign_node = ast.Assign([node.target], expr)
        return self.visit_Assign(assign_node)

    def visit_Assign(self, node):
        name_node = node.targets[0]
        index = None
        if hasattr(name_node, 'id'):
            name = name_node.id
        elif hasattr(name_node, 'value'):
            name = name_node.value.id
            index = self.visit(name_node)
        else:
            assert False, 'Unknown assignment type'

        val = None
        if name in self.in_intfs:
            # when interfaces are assigned visit_DataExpression is not allowed
            # because eval will execute the assignment and create extra gears
            # and connections for them
            for port in self.in_ports:
                if node.value.id == port.name:
                    val = port
                    break
            if val is None:
                for port in self.in_intfs:
                    if node.value.id == port:
                        val = self.in_intfs[port]
                        break
        else:
            val = self.visit_DataExpression(node.value)

        for var in self.variables:
            if var == name and not isinstance(self.variables[name], ht.Expr):
                self.variables[name] = ht.VariableDef(val, name)
                break

        if name in self.regs:
            if name not in self.hdl_locals:
                self.hdl_locals[name] = ht.RegDef(val, name)
            else:
                if index:
                    return ht.RegNextStmt(index, val)
                else:
                    return ht.RegNextStmt(self.hdl_locals[name], val)
        elif name in self.variables:
            if name not in self.hdl_locals:
                self.hdl_locals[name] = ht.VariableDef(val, name)
            if index:
                return ht.VariableStmt(index, val)
            else:
                return ht.VariableStmt(self.hdl_locals[name], val)
        elif name in self.in_intfs:
            if name not in self.hdl_locals:
                self.hdl_locals[name] = ht.IntfDef(val, name)
            if index:
                return ht.IntfStmt(index, val)
            else:
                return ht.IntfStmt(self.hdl_locals[name], val)
        elif name in self.out_intfs:
            if name not in self.hdl_locals:
                if not all([v is None for v in val.val]):
                    self.hdl_locals[name] = ht.IntfDef(val, name)
                else:
                    self.hdl_locals[name] = ht.IntfDef(self.out_ports, name)
            if index:
                return ht.IntfStmt(index, val)
            else:
                if (not hasattr(val, 'val')) or (not all(
                    [v is None for v in val.val])):
                    return ht.IntfStmt(self.hdl_locals[name], val)
        else:
            raise VisitError('Unknown assginment type')

    def visit_NameExpression(self, node):
        if node.id in self.in_intfs:
            return self.in_intfs[node.id]

        ret = eval_expression(node, self.locals)

        local_names = list(self.locals.keys())
        local_objs = list(self.locals.values())

        name_idx = None
        for i, obj in enumerate(local_objs):
            if ret is obj:
                name_idx = i
                break

        name = local_names[name_idx]

        return self.get_context_var(name)

    def visit_DataExpression(self, node):
        if not isinstance(node, ast.AST):
            return node

        try:
            return eval_data_expr(node, self.locals)
        except (NameError, AstTypeError, TypeError, AttributeError):
            return self.visit(node)

    def eval_expression(self, node):
        return eval(
            compile(ast.Expression(node), filename="<ast>", mode="eval"),
            self.locals, globals())

    def visit_Call(self, node):
        arg_nodes = [self.visit_DataExpression(arg) for arg in node.args]

        func_args = arg_nodes
        if all(isinstance(node, ht.ResExpr) for node in arg_nodes):
            func_args = []
            for arg in arg_nodes:
                if is_type(type(arg.val)) and not typeof(type(arg.val), Unit):
                    func_args.append(str(int(arg.val)))
                else:
                    func_args.append(str(arg.val))

        try:
            ret = eval(f'{node.func.id}({", ".join(func_args)})')
            return ht.ResExpr(ret)
        except:
            kwds = {}
            if hasattr(node.func, 'attr'):
                if node.func.attr is 'dtype':
                    func = eval_expression(node.func, self.hdl_locals)
                    ret = eval(f'func({", ".join(func_args)})')
                    return ht.ResExpr(ret)
                elif node.func.attr is 'tout':
                    return self.cast_return(func_args)
                else:
                    kwds['value'] = self.visit_DataExpression(node.func.value)
                    func = node.func.attr
            elif hasattr(node.func, 'id'):
                func = node.func.id
            else:
                # safe guard
                raise VisitError('Unrecognized func node in call')

            func_dispatch = None
            for m in self.call_modules:
                func_dispatch = getattr(m, f'Call_{func}', None)
                if func_dispatch:
                    break

            if func_dispatch:
                return func_dispatch(*func_args, **kwds)
            elif func in self.gear.params:
                assert isinstance(self.gear.params[func], TypingMeta)
                assert len(func_args) == 1, 'Cast with multiple arguments'
                return ht.CastExpr(
                    operand=func_args[0], cast_to=self.gear.params[func])

        # safe guard
        raise VisitError('Unrecognized func in call')

    def cast_return(self, arg_nodes):
        if isinstance(arg_nodes, list):
            assert len(arg_nodes) == len(self.gear.out_ports)
            input_vars = arg_nodes
        elif isinstance(arg_nodes,
                        ht.OperandVal) and len(self.gear.out_ports) > 1:
            assert len(arg_nodes.op) == len(self.gear.out_ports)
            input_vars = []
            for i in range(len(arg_nodes.op)):
                input_vars.append(
                    ht.SubscriptExpr(val=arg_nodes.op, index=ht.ResExpr(i)))
        else:
            assert len(self.out_ports) == 1
            input_vars = [arg_nodes]

        args = []
        for arg, port in zip(input_vars, self.gear.out_ports):
            t = port.dtype
            if typeof(t, Queue) or typeof(t, Tuple):
                if isinstance(arg, ht.ConcatExpr):
                    for i in range(len(arg.operands)):
                        if isinstance(arg.operands[i], ht.CastExpr) and (
                                arg.operands[i].cast_to == t[i]):
                            pass
                        else:
                            arg.operands[i] = ht.CastExpr(
                                operand=arg.operands[i], cast_to=t[i])

                args.append(arg)
            else:
                args.append(ht.CastExpr(operand=arg, cast_to=t))

        if len(args) == 1:
            return args[0]
        else:
            return args

    def visit_Tuple(self, node):
        items = [self.visit_DataExpression(item) for item in node.elts]
        return ht.ConcatExpr(items)

    def get_bin_expr(self, op, operand1, operand2):
        op1 = self.visit_DataExpression(operand1)
        op2 = self.visit_DataExpression(operand2)
        if isinstance(op, ast.MatMult):
            return ht.ConcatExpr((op2, op1))
        else:
            operator = opmap[type(op)]
            return ht.BinOpExpr((op1, op2), operator)

    def visit_BinOp(self, node):
        return self.get_bin_expr(node.op, node.left, node.right)

    def visit_Attribute(self, node):
        expr = self.visit(node.value)
        if isinstance(expr, ht.AttrExpr):
            return ht.AttrExpr(expr.val, expr.attr + [node.attr])
        else:
            return ht.AttrExpr(expr, [node.attr])

    def visit_Compare(self, node):
        return self.get_bin_expr(node.ops[0], node.left, node.comparators[0])

    def visit_BoolOp(self, node):
        return self.get_bin_expr(node.op, node.values[0], node.values[1])

    def visit_UnaryOp(self, node):
        operand = self.visit_DataExpression(node.operand)

        if isinstance(operand, ht.ResExpr):
            return self.visit_DataExpression(node)
        else:
            operator = opmap[type(node.op)]
            return ht.UnaryOpExpr(operand, operator)

        return self.visit_DataExpression(node)

    def visit_If(self, node):
        expr = self.visit_DataExpression(node.test)

        if isinstance(expr, ht.ResExpr):
            if bool(expr.val):
                for stmt in node.body:
                    hdl_stmt = self.visit(stmt)
                    if hdl_stmt is not None:
                        self.scope[-1].stmts.append(hdl_stmt)
            elif hasattr(node, 'orelse'):
                for stmt in node.orelse:
                    hdl_stmt = self.visit(stmt)
                    if hdl_stmt is not None:
                        self.scope[-1].stmts.append(hdl_stmt)
            return None
        else:
            hdl_node = ht.IfBlock(_in_cond=expr, stmts=[])
            self.visit_block(hdl_node, node.body)
            if hasattr(node, 'orelse') and node.orelse:
                else_expr = ht.create_oposite(expr)
                hdl_node_else = ht.IfBlock(_in_cond=else_expr, stmts=[])
                self.visit_block(hdl_node_else, node.orelse)
                top = ht.ContainerBlock(stmts=[hdl_node, hdl_node_else])
                return top
            else:
                return hdl_node

    def visit_While(self, node):
        test = self.visit_DataExpression(node.test)
        hdl_node = ht.Loop(
            _in_cond=test,
            stmts=[],
            _exit_cond=ht.create_oposite(test),
            multicycle=[])

        return self.visit_block(hdl_node, node.body)

    def visit_For(self, node):
        res = self.visit_DataExpression(node.iter)

        if isinstance(node.target, ast.Tuple):
            names = [x.id for x in node.target.elts]
        else:
            names = [node.target.id]

        func_dispatch = None
        for m in self.call_modules:
            func_dispatch = getattr(m, f'For_{node.iter.func.id}', None)
            if func_dispatch:
                break

        if func_dispatch:
            return func_dispatch(self, node, res, names)
        else:
            raise VisitError('Unsuported func in for loop')

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Yield):
            return self.visit_Yield(node.value)
        else:
            self.generic_visit(node)

    def visit_Yield(self, node):
        if isinstance(node.value, ast.Tuple) and len(self.out_ports) > 1:
            expr = [
                self.visit_DataExpression(item) for item in node.value.elts
            ]
        else:
            expr = super().visit(node.value)
        return ht.Yield(
            expr=self.cast_return(expr), stmts=[], ports=self.out_ports)

    def visit_AsyncFunctionDef(self, node):
        hdl_node = ht.Module(
            in_ports=self.in_ports,
            out_ports=self.out_ports,
            locals=self.hdl_locals,
            regs=self.regs,
            variables=self.variables,
            intfs=self.in_intfs,
            out_intfs=self.out_intfs,
            stmts=[])

        return self.visit_block(hdl_node, node.body)


class HdlAstVisitor:
    def visit(self, node):
        """Visit a node."""
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node):
        """Called if no explicit visitor function exists for a node."""
        if hasattr(node, 'stmts'):
            for stmt in node.stmts:
                self.visit(stmt)


class PrintVisitor(HdlAstVisitor):
    def __init__(self):
        self.indent = 0

    def enter_block(self):
        self.indent += 4

    def exit_block(self):
        self.indent -= 4

    def write_line(self, line):
        print(f'{" "*self.indent}{line}')

    def generic_visit(self, node):
        if hasattr(node, 'stmts'):
            line = f'{node.__class__.__name__}('
            for field, value in ast.iter_fields(node):
                if field == 'stmts':
                    continue

                line += f'{field}={repr(value)}, '

            self.write_line(f'{line}stmts=[')
            self.enter_block()

            for stmt in node.stmts:
                self.visit(stmt)

            self.exit_block()
            self.write_line(f']')
        else:
            self.write_line(repr(node))


def pprint(node):
    PrintVisitor().visit(node)
