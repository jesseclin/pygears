import hdl_types as ht
from pygears.typing import Uint, bitw

from .hdl_compile import HDLWriter, parse_gear_body
from .hdl_utils import state_expr
from .inst_visit import InstanceVisitor
from .sv_expression import svexpr
from .util import svgen_typedef

reg_template = """
always_ff @(posedge clk) begin
    if(rst | rst_cond) begin
        {0}_reg = {1};
    end else if ({0}_en) begin
        {0}_reg = {0}_next;
    end
end
"""


class SVCompiler(InstanceVisitor):
    def __init__(self, visit_var, writer):
        self.writer = writer
        self.visit_var = visit_var

    def enter_block(self, block):
        if getattr(block, 'in_cond', False):
            self.writer.line(f'if ({svexpr(block.in_cond)}) begin')

        if getattr(block, 'in_cond', True):
            self.writer.indent += 4

    def exit_block(self, block=None):
        if getattr(block, 'in_cond', True):
            self.writer.indent -= 4
            self.writer.line(f'end')

    def visit_AssignValue(self, node):
        if node.width:
            self.writer.line(
                f"{node.target} = {node.width}'({svexpr(node.val)});")
        else:
            self.writer.line(f"{node.target} = {svexpr(node.val)};")

    def visit_CombBlock(self, node):
        if not node.stmts and not node.dflts:
            return
        self.writer.line(f'// Comb block for: {self.visit_var}')
        self.writer.line(f'always_comb begin')

        self.visit_HDLBlock(node)

        self.writer.line('')

    def visit_CombSeparateStmts(self, node):
        self.writer.line(f'// Comb statements for: {self.visit_var}')
        for stmt in node.stmts:
            if stmt.width:
                self.writer.line(
                    f"assign {stmt.target} = {stmt.width}'({svexpr(stmt.val)});"
                )
            else:
                self.writer.line(f"assign {stmt.target} = {svexpr(stmt.val)};")
        self.writer.line('')

    def visit_HDLBlock(self, node):
        self.enter_block(node)

        for name, val in node.dflts.items():
            if val.width:
                self.writer.line(f"{name} = {val.width}'({svexpr(val.val)});")
            else:
                self.writer.line(f"{name} = {svexpr(val.val)};")

        for stmt in node.stmts:
            self.visit(stmt)

        self.exit_block(node)


data_func_gear = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


def write_module(node, sv_stmts, writer, block_conds, state_num):
    for name, expr in node.regs.items():
        writer.block(svgen_typedef(expr.dtype, name))
        writer.line(f'logic {name}_en;')
        writer.line(f'{name}_t {name}_reg, {name}_next;')
        writer.line()

    for name, val in node.intfs.items():
        writer.line(f'dti#({int(val.dtype)}) {name}();')
        writer.block(svgen_typedef(val.dtype, name))
        writer.line(f'{name}_t {name}_s;')
        writer.line(f"assign {name}.data = {name}_s;")
    writer.line()

    if state_num > 0:
        writer.block(svgen_typedef(Uint[bitw(state_num)], 'state'))
        writer.line(f'logic state_en;')
        writer.line(f'state_t state_reg, state_next;')
        writer.line()

    for name, expr in node.variables.items():
        writer.block(svgen_typedef(expr.dtype, name))
        writer.line(f'{name}_t {name}_v;')
        writer.line()

    for cond, values in block_conds.items():
        for id in values:
            c_name = ht.cond_name.substitute(cond_type=cond, block_id=id)
            writer.line(f'logic {c_name};')
    writer.line()

    if node.regs:
        if state_num > 0:
            rst_cond = state_expr([state_num], node.rst_cond)
        else:
            rst_cond = node.rst_cond
        writer.line(f'logic rst_cond;')
        writer.line(f'assign rst_cond = {svexpr(rst_cond)};')

    for name, expr in node.regs.items():
        writer.block(reg_template.format(name, int(expr.val)))

    if state_num > 0:
        writer.block(reg_template.format('state', 0))

    for name, val in sv_stmts.items():
        SVCompiler(name, writer).visit(val)


def compile_gear_body(gear, function_impl_paths=None):
    hdl_ast, res, block_conds, state_num = parse_gear_body(
        gear, function_impl_paths)
    writer = HDLWriter()
    write_module(hdl_ast, res, writer, block_conds, state_num)

    return '\n'.join(writer.svlines)


def compile_gear(gear, template_env, context, function_impl_paths=None):
    context['svlines'] = compile_gear_body(gear, function_impl_paths)

    return template_env.render_string(data_func_gear, context)
