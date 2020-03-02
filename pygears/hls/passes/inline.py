from .utils import Scope, HDLVisitor, res_true, add_to_list, ir, res_false, IrExprRewriter


class Inliner(IrExprRewriter):
    def __init__(self, forwarded):
        self.forwarded = forwarded

    def visit_Name(self, node):
        if ((node.name in self.forwarded) and (node.ctx == 'load')):
            return self.forwarded[node.name]

        return None


class InlineValues(HDLVisitor):
    def __init__(self, ctx):
        self.ctx = ctx
        self.block_stack = []
        self.forwarded = Scope()

    @property
    def block(self):
        if not self.block_stack:
            return None

        return self.block_stack[-1]

    def inline_expr(self, node):
        new_node = Inliner(self.forwarded).visit(node)
        if new_node is None:
            return node

        return new_node

    def merge_subscope(self, block):
        subscope = self.forwarded.cur_subscope
        self.forwarded.upscope()

        for name, val in subscope.items.items():
            if block.in_cond != res_true:
                if name in self.forwarded:
                    prev_val = self.forwarded[name]
                else:
                    prev_val = self.ctx.ref(name)

                val = ir.ConditionalExpr((val, prev_val), block.in_cond)

            self.forwarded[name] = val

    def FuncReturn(self, node):
        node.expr = self.inline_expr(node.expr)

        return node

    def AssignValue(self, node: ir.AssignValue):
        node.val = self.inline_expr(node.val)

        def del_forward_subvalue(target):
            if isinstance(target, ir.Name):
                if target.name in self.forwarded:
                    del self.forwarded[target.name]

            elif isinstance(target, ir.SubscriptExpr):
                del_forward_subvalue(target.val)

        def set_forward_subvalue(target, val):
            if isinstance(target, ir.Name):
                if target.name not in self.forwarded:
                    if target.obj.reg:
                        return None

                self.forwarded[target.name]
            elif isinstance(target, ir.SubscriptExpr):
                if isinstance(target.index, ir.ResExpr):
                    index_val = target.index.val
                    base_val = set_forward_subvalue(target)
                    if base_val is None:
                        return None

                    base_val[index_val] = val
                else:
                    del_forward_subvalue(target)

        def forward_value(target, val):
            if isinstance(target, ir.Name):
                self.forwarded[target.name] = val
            elif isinstance(target, ir.ConcatExpr):
                for i, t in enumerate(target.operands):
                    forward_value(t, ir.SubscriptExpr(val, ir.ResExpr(i)))
            elif isinstance(target, ir.SubscriptExpr):
                set_forward_subvalue(target, val)

        val = node.val
        if isinstance(val, ir.Await):
            val = val.expr

        if isinstance(val, ir.ConcatExpr):
            val = ir.ConcatExpr(operands=[
                op.expr if isinstance(op, ir.Await) else op
                for op in val.operands])

        forward_value(node.target, val)

        return node

    def Statement(self, stmt: ir.Statement):
        return stmt

    def BaseBlock(self, block: ir.BaseBlock):
        stmts = []

        self.block_stack.append(block)

        for stmt in block.stmts:
            add_to_list(stmts, self.visit(stmt))

        self.block_stack.pop()

        block.stmts = stmts
        return block

    def HDLBlock(self, block: ir.HDLBlock):
        block.in_cond = self.inline_expr(block.in_cond)

        if not isinstance(self.block, ir.IfElseBlock):
            self.forwarded.subscope()

        res = self.BaseBlock(block)

        if isinstance(self.block, ir.IfElseBlock):
            return res

        block.exit_cond = self.inline_expr(block.exit_cond)

        self.merge_subscope(block)

        return res

    def LoopBlock(self, block: ir.LoopBlock):
        block.in_cond = self.inline_expr(block.in_cond)

        looped_init = False
        for name in self.forwarded:
            if (isinstance(self.ctx.scope[name], ir.Variable)
                    and self.ctx.scope[name].reg):
                if not looped_init:
                    looped_init = True
                    looped_var_name = self.ctx.find_unique_name('_looped')
                    self.ctx.scope[looped_var_name] = ir.Variable(
                        looped_var_name,
                        val=res_false,
                        reg=True,
                    )

                self.forwarded[name] = ir.ConditionalExpr(
                    (self.ctx.ref(name), self.forwarded[name]),
                    self.ctx.ref(looped_var_name))

        self.forwarded.subscope()

        block = self.BaseBlock(block)

        block.exit_cond = self.inline_expr(block.exit_cond)

        self.merge_subscope(block)

        if looped_init:
            block.stmts.append(
                ir.AssignValue(target=self.ctx.ref(looped_var_name),
                               val=res_true))

        return block

    def IfElseBlock(self, block: ir.IfElseBlock):
        self.block_stack.append(block)

        subscopes = []
        forwards = set()

        stmts = []
        for stmt in block.stmts:
            self.forwarded.subscope()

            add_to_list(stmts, self.visit(stmt))
            subs = self.forwarded.cur_subscope
            subs.in_cond = stmts[-1].in_cond
            subscopes.append(subs)
            forwards.update(subs.items.keys())

            self.forwarded.upscope()

        for name in forwards:
            if name in self.forwarded:
                val = self.forwarded[name]
            else:
                val = self.ctx.ref(name)

            for subs in reversed(subscopes):
                if name in subs.items:
                    val = ir.ConditionalExpr((subs.items[name], val),
                                             cond=subs.in_cond)

            self.forwarded[name] = val

        block.stmts = stmts
        self.block_stack.pop()
        return block

    def generic_visit(self, node):
        pass


class InlineResValues(HDLVisitor):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.forwarded = Scope()

    def inline_expr(self, node):
        new_node = Inliner(self.forwarded).visit(node)
        if new_node is None:
            return node

        return new_node

    def AssignValue(self, node: ir.AssignValue):
        node.val = self.inline_expr(node.val)
        if isinstance(node.target, ir.Name) and isinstance(
                node.val, ir.ResExpr):
            self.forwarded[node.target.name] = node.val

    def HDLBlock(self, block: ir.HDLBlock):
        block.in_cond = self.inline_expr(block.in_cond)

        prev_scope = self.forwarded
        self.forwarded = Scope()

        self.BaseBlock(block)

        block.exit_cond = self.inline_expr(block.exit_cond)

        self.forwarded = prev_scope


def inline_res(modblock, ctx):
    InlineResValues(ctx).visit(modblock)
    return modblock


def inline(modblock, ctx):
    InlineValues(ctx).visit(modblock)
    return modblock
