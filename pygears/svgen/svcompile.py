import ast
import inspect

from .hdl_ast import HdlAst, RegFinder
from .util import svgen_typedef
from .hdl_preprocess import InstanceVisitor, SVCompilerPreprocess, svexpr

reg_template = """
always_ff @(posedge clk) begin
    if(rst | {1}) begin
        {0}_reg = {1};
    end else if ({0}_en) begin
        {0}_reg = {0}_next;
    end
end
"""


class DefaultFound(Exception):
    pass


class SVWriter:
    def __init__(self):
        self.indent = 0
        self.svlines = []

    def line(self, line=''):
        if not line:
            self.svlines.append('')
        else:
            self.svlines.append(f'{" "*self.indent}{line}')

    def block(self, block):
        for line in block.split('\n'):
            self.line(line)


class SVCompiler(InstanceVisitor):
    def __init__(self, visit_var, writer):
        self.writer = writer
        self.visit_var = visit_var

    def enter_block(self, block):
        if getattr(block, 'in_cond', False):
            self.writer.line(f'if ({block.in_cond}) begin')

        if getattr(block, 'in_cond', True):
            self.writer.indent += 4

    def enter_else_block(self, block):
        self.writer.line(f'else begin')
        self.writer.indent += 4

    def exit_block(self, block=None):
        if getattr(block, 'in_cond', True):
            self.writer.indent -= 4
            self.writer.line(f'end')

    def visit_AssignValue(self, node):
        if node.width:
            self.writer.line(f"{node.target} = {node.width}'({node.val});")
        else:
            self.writer.line(f"{node.target} = {node.val};")

    def visit_CombBlock(self, node):
        self.writer.line(f'// Comb block for: {self.visit_var}')
        self.writer.line(f'always_comb begin')

        self.visit_SVBlock(node)

        self.writer.line('')

    def visit_SVBlock(self, node):
        self.enter_block(node)

        for name, val in node.dflts.items():
            if val.width:
                self.writer.line(f"{name} = {val.width}'({val.val});")
            else:
                self.writer.line(f"{name} = {val.val};")

        if not hasattr(node, 'else_cond') or node.else_cond is None:
            for stmt in node.stmts:
                self.visit(stmt)

            self.exit_block(node)

        else:
            assert len(node.stmts) == 2

            self.visit(node.stmts[0])
            self.exit_block(node)

            self.enter_else_block(node)
            self.visit(node.stmts[1])
            self.exit_block(node)


data_func_gear = """
{%- import 'snippet.j2' as snippet -%}

{% call snippet.module_with_intf_structs(module_name, intfs, intfs, comment) %}

{{svlines|indent(4,True)}}

{%- endcall %}
"""


def write_module(node, sv_stmts, writer):
    for name, expr in node.regs.items():
        writer.block(svgen_typedef(expr.dtype, name))
        writer.line(f'logic {name}_en;')
        # writer.line(f'logic {name}_rst;')
        writer.line(f'{name}_t {name}_reg, {name}_next;')
        writer.line()

    for name, expr in node.variables.items():
        writer.block(svgen_typedef(expr.dtype, name))
        writer.line(f'{name}_t {name}_v;')
        writer.line()

    for i, stage in enumerate(node.stages):
        if stage.cycle_cond is not None:
            writer.line(f'logic cycle_cond_stage_{i};')

        if stage.exit_cond is not None:
            writer.line(f'logic exit_cond_stage_{i};')

    for i, stage in enumerate(node.stages):
        stage_id = ''.join([str(s.state_id) for s in node.stages[1:]])

        if stage.cycle_cond is not None:
            writer.line(f'assign cycle_cond_stage_{stage_id} ='
                        f' {svexpr(stage.cycle_cond)};')

        if stage.exit_cond is not None:
            if stage.cycle_cond is not None:
                writer.line((f'assign exit_cond_stage_{stage_id} ='
                             f' ({svexpr(stage.exit_cond)})'
                             f'&& cycle_cond_stage_{stage_id};'))
            else:
                writer.line((f'assign exit_cond_stage_{stage_id} ='
                             f' {svexpr(stage.exit_cond)};'))

    for name, expr in node.regs.items():
        writer.block(
            reg_template.format(name, int(expr.val), svexpr(node.exit_cond)))

    for name, val in sv_stmts.items():
        SVCompiler(name, writer).visit(val)


def compile_gear_body(gear):
    body_ast = ast.parse(inspect.getsource(gear.func)).body[0]
    # import astpretty
    # astpretty.pprint(body_ast)

    # find registers and variables
    v = RegFinder(gear)
    v.visit(body_ast)
    v.clean_variables()

    # py ast to hdl ast
    hdl_ast = HdlAst(gear, v.regs, v.variables).visit(body_ast)

    # pprint(hdl_ast)

    res = {}

    for name in hdl_ast.regs:
        # res[name] = SVCompilerPreprocess(name, ['_en', '_rst']).visit(hdl_ast)
        res[name] = SVCompilerPreprocess(name, ['_en']).visit(hdl_ast)

    for name in hdl_ast.variables:
        res[name] = SVCompilerPreprocess(name).visit(hdl_ast)

    for port in hdl_ast.out_ports:
        res[port.name] = SVCompilerPreprocess(port.name,
                                              ['.valid']).visit(hdl_ast)

    for port in hdl_ast.in_ports:
        res[port.name] = SVCompilerPreprocess(port.name,
                                              ['.ready']).visit(hdl_ast)

    writer = SVWriter()
    write_module(hdl_ast, res, writer)

    return '\n'.join(writer.svlines)


def compile_gear(gear, template_env, context):
    context['svlines'] = compile_gear_body(gear)

    return template_env.render_string(data_func_gear, context)
