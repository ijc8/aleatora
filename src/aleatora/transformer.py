"""Transform standard Python generators into Aleatora streams.

Streams are similar to generators, in that they likewise lazily yield a sequence of values,
but they are distinct in that they are typically immutable and may be replayed from any point.

Python generators are advanced via `next()`, which returns the next value and mutates the
generator object, preventing earlier points in the sequence from being accessed or re-executed.
Streams are advanced by calling the stream. This does not (usually) mutate the stream,
but returns a tuple (value, next_stream), where next_stream represents the rest of the stream.
Thus, a stream may be played back from an earlier point by simply calling that point again.

This transformation is triggered via decorator, @generator_stream, which turns a generator function
(which returns a generator object when called) into a stream function (which returns a stream when called).
The transformation works internally by parsing the function, transforming its AST, and executing the result.
The generator function is transformed such that `yield` is no longer necessary; instead, values are yielded,
and the computation is suspended, by returning a value and the next function to call.
This requires splitting the generator function up into many smaller functions, each representing one basic
block of a control-flow graph. For example, when the original generator yields, the corresponding function
returns ('yield', <next function to call>, <local variables>)

The transformation is careful to preserve the semantics of the original generator function,
including if/else, for/else, while/else, break, continue, return and (partially) try/except/else/finally,
with the following caveats/known issues (TODO):
- Control flow breaks (break/continue/return) are not supported in `try` blocks.
- `finally` is not supported.
- Exception variables will not survive past control flow breaks
  (and they will not implicitly delete locals with the same name).
- `yield from` is not supported.
- `yield` as an expression is not supported (it must appear as a statement).
- Local variables (except for arguments) are initialized as `None`, so accessing them before they are set
  will not raise `UnboundLocalError`.
  (Fixing this will probably require translating local access into attribute access on a special object
   which raises `UnboundLocalError` instead of `AttributeError`.)
- Using `del` on locals (without setting the local afterward) is not supported.
"""

import ast
import inspect

import astor

from . import core


## AST helpers

def get_arg_names(args):
    "Return a list of all the argument names in an ast.arguments object."
    names = [a.arg for a in args.args]
    if args.vararg:
        names.append(args.vararg.arg)
    names += [a.arg for a in args.kwonlyargs]
    if args.kwarg:
        names.append(args.kwarg.arg)
    return names


class VariableFinder(ast.NodeVisitor):
    def __init__(self):
        self.store_names = set()
        self.global_names = set()
        self.nonlocal_names = set()
        self.inside = False

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            self.store_names.add(node.id)

    def visit_Global(self, node):
        for name in node.names:
            self.global_names.add(name)
    
    def visit_Nonlocal(self, node):
        for name in node.names:
            self.nonlocal_names.add(name)

    def visit_FunctionDef(self, node):
        if not self.inside:
            self.inside = True
            self.store_names |= set(get_arg_names(node.args))
            self.generic_visit(node)
            self.inside = False

def get_variables(node):
    "Get all the local, nonlocal, and global variable names in a function definition (including arguments)."
    vf = VariableFinder()
    vf.visit(node)
    local_names = vf.store_names - vf.nonlocal_names - vf.global_names
    return (local_names, vf.nonlocal_names, vf.global_names)


## `while` -> `for` transformer

# Transform this:
#
# for var_name in iter_expr:
#     loop_body
# else:
#     else_body
#
# into:
#
# it = iter(<iter_expr>)
# keep_going = True
# while keep_going:
#     try:
#         <var_name> = next(it)
#     except StopIteration:
#         keep_going = False
#     else:
#         <loop_body>
# else:
#     <else_body>

# We can't just use a break in the `except` because that would also trigger the while's `else`.
# We could add an additional bool like `normal_exit` + an `if not normal_exit` in the else for this case, but I think this is cleaner.

# Writing ASTs by hand is tedious, so let's do this instead:

class TemplateTransformer(ast.NodeTransformer):
    "Fill in a template AST with named fragments."

    # Hygiene counter.
    id = 0

    def __init__(self, fragment_map):
        super().__init__()
        self.fragment_map = fragment_map
        self.hygiene_map = {}
    
    def visit_Expr(self, node):
        if isinstance(node.value, ast.Name):
            return self.fragment_map.get(node.value.id, node)
        self.generic_visit(node)
        return node
    
    def visit_Name(self, node):
        if node.id in self.fragment_map:
            return self.fragment_map[node.id]
        elif node.id.startswith('_'):
            if node.id not in self.hygiene_map:
                self.hygiene_map[node.id] = f'{node.id}_{self.id}'
                TemplateTransformer.id += 1
            return ast.Name(id=self.hygiene_map[node.id], ctx=node.ctx)
        else:
            return node

# Template for for->while transform.
# Caps will be replaced by AST fragments, _vars will be replaced with hygenic names.
def for_template():
    _it = iter(ITER_EXPR)
    _keep_going = True
    while _keep_going:
        try:
            VAR_NAME = next(_it)
        except StopIteration:
            _keep_going = False
        else:
            LOOP_BODY
    else:
        ELSE_BODY

class RewriteFor(ast.NodeTransformer):
    def visit_For(self, node):
        tt = TemplateTransformer({
            'ITER_EXPR': node.iter,
            'VAR_NAME': node.target,
            'LOOP_BODY': node.body,
            'ELSE_BODY': node.orelse,
        })
        self.generic_visit(node)
        return tt.visit(ast.parse(inspect.getsource(for_template)).body[0]).body


## Main transformation: function definition -> control-flow graph -> interlinked function definitions

def make_cfg(name, body, local_names):
    "Transform a sequence of statements into a control-flow graph (CFG)."

    id = -1
    local_tuple = ast.Tuple(elts=[ast.Name(id=local, ctx=ast.Load()) for local in local_names], ctx=ast.Load())

    # TODO: Only transform a branch or loop if it has a yield somewhere in its subtree.
    def build_cfg(statements, successor=None, continue_target=None, break_target=None):
        # print('build_cfg', statements, successor)
        nonlocal id
        id += 1
        cfg = {'id': id, 'name': ast.Name(id=f'_{name}_{id:x}', ctx=ast.Load()), 'children': []}
        stmts = []
        for i, statement in enumerate(statements):
            # print(astor.dump_tree(statement))
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Yield):
                # Break off into next CFG.
                rest_cfg = build_cfg(statements[i+1:], successor, continue_target, break_target)
                cfg['children'].append(rest_cfg)
                stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('yield'), statement.value.value, rest_cfg['name'], local_tuple], ctx=ast.Load())))
                cfg['statements'] = stmts
                return cfg
            elif isinstance(statement, ast.If):
                rest_cfg = build_cfg(statements[i+1:], successor, continue_target, break_target)
                then_cfg = build_cfg(statement.body, rest_cfg['name'], continue_target, break_target)
                else_cfg = build_cfg(statement.orelse, rest_cfg['name'], continue_target, break_target)
                stmts.append(ast.If(test=statement.test,
                                    body=[ast.Return(ast.Tuple(elts=[ast.Str('bounce'), then_cfg['name'], local_tuple], ctx=ast.Load()))],
                                    orelse=[ast.Return(ast.Tuple(elts=[ast.Str('bounce'), else_cfg['name'], local_tuple], ctx=ast.Load()))]))
                cfg['statements'] = stmts
                cfg['children'] += [then_cfg, else_cfg, rest_cfg]
                return cfg
            elif isinstance(statement, ast.While):
                cond_cfg = build_cfg([])
                rest_cfg = build_cfg(statements[i+1:], successor, continue_target, break_target)
                then_cfg = build_cfg(statement.body, cond_cfg['name'], cond_cfg['name'], rest_cfg['name'])
                else_cfg = build_cfg(statement.orelse, rest_cfg['name'], continue_target, break_target)
                cond_cfg['statements'] = [ast.If(test=statement.test,
                                                 body=[ast.Return(ast.Tuple(elts=[ast.Str('bounce'), then_cfg['name'], local_tuple], ctx=ast.Load()))],
                                                 orelse=[ast.Return(ast.Tuple(elts=[ast.Str('bounce'), else_cfg['name'], local_tuple], ctx=ast.Load()))])]
                stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('bounce'), cond_cfg['name'], local_tuple], ctx=ast.Load())))
                cfg['statements'] = stmts
                cfg['children'] += [cond_cfg, then_cfg, else_cfg, rest_cfg]
                return cfg
            elif isinstance(statement, ast.Try):
                # When executing the chunks inside the `try`, we need:
                # - the CFG names and types of the various exception handlers
                # - the CFG name of the `else` block (as `successor`)
                #  and each block within the `try` needs to be wrapped in `try...except...else`.
                # Inside each exception handler, we need:
                # - the CFG name of the `finally` block (as `successor`)
                # Inside the `else` block, we need:
                # - the CFG name of the `finally` block (as `successor`)
                # `try` does not need a link to the `finally` block, because
                # all possible successors (the exception handlers and `else`) have it.
                # What about nested `try`s? Need to keep track of a *stack* of handlers.
                # The behavior of `finally` is quite tricky.
                # It needs to re-raise exceptions (unless it hits break, continue, return),
                # happen *before* a break, continue, or return in a `try`,
                # and override `try`'s return value.
                # Also, get_variables should also consider names like `x` in `except E as x`... but only inside the exception.
                # (see https://stackoverflow.com/questions/29268892/python-3-exception-deletes-variable-in-enclosing-scope-for-unknown-reason)

                # TODO: For now, we will ignore `finally`, disallow yield/break/continue/return inside `try`s,
                # and not pass the exception variable across control-flow boundaries in exception handlers.
                assert statement.finalbody == [], "`finally` is not supported"
                rest_cfg = build_cfg(statements[i+1:], successor, continue_target, break_target)
                for handler in statement.handlers:
                    handler_cfg = build_cfg(handler.body, rest_cfg['name'], continue_target, break_target)
                    handler.body = [ast.Return(ast.Tuple(elts=[ast.Str('bounce'), handler_cfg['name'], local_tuple], ctx=ast.Load()))]
                    cfg['children'].append(handler_cfg)
                else_cfg = build_cfg(statement.orelse, rest_cfg['name'], continue_target, break_target)
                cfg['children'] += [else_cfg, rest_cfg]
                statement.orelse = [ast.Return(ast.Tuple(elts=[ast.Str('bounce'), else_cfg['name'], local_tuple], ctx=ast.Load()))]
                stmts.append(statement)
                stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('bounce'), rest_cfg['name'], local_tuple], ctx=ast.Load())))
                cfg['statements'] = statements
                return cfg
            elif isinstance(statement, ast.For):
                # `for`s should be transformed into `while`s at an earlier stage.
                assert False
            elif isinstance(statement, ast.Return):
                # Not really necessary to return locals here, but we do so anyway for inspection/debugging purposes.
                stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('return'), statement.value, local_tuple], ctx=ast.Load())))
                cfg['statements'] = stmts
                return cfg
            elif isinstance(statement, ast.Continue):
                stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('bounce'), continue_target, local_tuple], ctx=ast.Load())))
                cfg['statements'] = stmts
                return cfg
            elif isinstance(statement, ast.Break):
                stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('bounce'), break_target, local_tuple], ctx=ast.Load())))
                cfg['statements'] = stmts
                return cfg
            else:
                stmts.append(statement)
        if successor:
            stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('bounce'), successor, local_tuple], ctx=ast.Load())))
        else:
            # Not really necessary to return locals here, but we do so anyway for inspection/debugging purposes.
            stmts.append(ast.Return(ast.Tuple(elts=[ast.Str('return'), ast.NameConstant(value=None), local_tuple], ctx=ast.Load())))
        cfg['statements'] = stmts
        return cfg
    return build_cfg(body)

def convert_cfg(cfg, local_names, nonlocal_names, global_names):
    "Convert a control-flow graph into linked function definitions."
    declarations = []
    if nonlocal_names:
        declarations.append(ast.Nonlocal(names=nonlocal_names))
    if global_names:
        declarations.append(ast.Global(names=global_names))
    defs = []
    def dfs(cfg):
        args = ast.arguments(args=[ast.arg(arg=local, annotation=None) for local in local_names],
                             vararg=None, kwarg=None, kwonlyargs=[], kw_defaults=[], defaults=[])
        defs.append(ast.FunctionDef(name=cfg['name'].id, args=args,
                                    body=declarations + cfg['statements'], decorator_list=[]))
        for child in cfg['children']:
            dfs(child)
    dfs(cfg)
    return defs


## Final stretch: create an entry point into the interlinked function definitions, and make it a stream.

class GeneratorStream(core.Stream):
    """Stream representing a transformed generator.
    
    In addition to yielding elements and returning a final value (as in any stream),
    this may internally 'bounce' back into the generator to help recreate the original flow control.
    """

    def __init__(self, generated_fn, locals=()):
        self.generated_fn = generated_fn
        self.locals = locals
    
    def __call__(self):
        fn, locals = self.generated_fn, self.locals
        while True:
            inst, *args = fn(*locals)
            if inst == 'bounce':
                fn, locals = args
            else:
                break
        if inst == 'yield':
            value, fn, locals = args
            return (value, GeneratorStream(fn, locals))
        elif inst == 'return':
            return core.Return(args[0])

def generator_stream(f=None, debug=False):
    """Decorator for converting a standard Python generator into a stream.
    
    Streams are similar to generators (they lazily compute and yield values on demand),
    but they are distinct in that their point in the computation may be 'saved' and restored
    later, including the contents of local variables.
    """
    def helper(f):
        tree = ast.parse(inspect.getsource(f))
        fn = RewriteFor().visit(tree.body[0])
        if debug:
            print(astor.to_source(fn))
        args = get_arg_names(fn.args)
        local_names, nonlocal_names, global_names = get_variables(fn)
        # For simplicity in calling convention, we want args to always occur before other locals:
        local_names = args + list(local_names - set(args))
        name = f'{f.__qualname__}_{hash(f):x}'
        cfg = make_cfg(name, fn.body, local_names)
        defs = convert_cfg(cfg, local_names, nonlocal_names, global_names)

        args = ast.Tuple(elts=[ast.Name(id=arg, ctx=ast.Load()) for arg in args] +
                            [ast.NameConstant(None) for _ in range(len(local_names) - len(args))],
                        ctx=ast.Load())
        entry = ast.FunctionDef(name=f'_{name}_entry', args=fn.args, decorator_list=[], body=[
            ast.Return(ast.Call(func=ast.Name(id='GeneratorStream', ctx=ast.Load()), args=[cfg['name'], args], keywords=[]))
        ])
        # TODO: Some special initial value in place of None.
        # (Some kind of "Undefined" that is unique to this and throws exceptions when you try to do anything with it?)
        defs.append(entry)
        defs.append(ast.Expr(ast.Name(id='GeneratorStream', ctx=ast.Load())))
        m = ast.fix_missing_locations(ast.Module(defs))

        if debug:
            print(astor.to_source(m))
        # TODO: Could hide all of the global functions generated by this in a temporary scope.
        # This would also make it easy to give the entry function the same name as the
        # original function without accidentally overwriting a global.
        exec(compile(m, f.__code__.co_filename, 'exec'), globals())
        return globals()[f'_{name}_entry']
    if f:
        return helper(f)
    return helper


## Examples

if __name__ == '__main__':
    import random

    @generator_stream(debug=True)
    def foo():
        yield 1
        if random.random() > 0.5:
            yield 2
            print("yay")
            yield 3
        else:
            yield 4
            print("nay")
            yield 5
        print("almost done")
        yield 6
        print("done")
        return 7

    @generator_stream
    def grand():
        while True:
            yield random.random()

    @generator_stream
    def bar():
        i = 0
        while i < 3:
            print(i)
            yield i
            i += 1

    @generator_stream(debug=True)
    def baz(i):
        while i > 0:
            yield i
            if i % 3 == 0:
                print(i, "is a multiple of 3")
                i -= 2
                continue
            if i % 11 == 0:
                print("Yipee!", i, "is a multiple of 11")
                print("That's so nice we'll yield it twice.")
                yield i
                break
            i -= 1
        print("All done!")
        yield 0

    @generator_stream(debug=True)
    def foo(n):
        for i in range(n):
            yield i

    @generator_stream(debug=True)
    def test_function():
        print('hi')
        for i in range(10):
            yield i
        l = [1,3,5,7]
        for x in l:
            if x % 2 == 0:
                print(x, 'is even!')
                break
            yield x
        else:
            print('No even numbers!')
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    yield i, j, k

    x = 5

    @generator_stream(debug=True)
    def global_test():
        global x
        yield x
        x += 1
        yield x