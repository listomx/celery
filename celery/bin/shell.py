import os
import sys
from importlib import import_module

import click

from celery.bin.base import CeleryCommand, CeleryOption


def invoke_fallback_shell(locals):
    import code
    try:
        import readline
    except ImportError:
        pass
    else:
        import rlcompleter
        readline.set_completer(
            rlcompleter.Completer(locals).complete)
        readline.parse_and_bind('tab:complete')
    code.interact(local=locals)


def invoke_bpython_shell(locals):
    import bpython
    bpython.embed(locals)


def invoke_ipython_shell(locals):
    for ip in (_ipython, _ipython_pre_10,
               _ipython_terminal, _ipython_010,
               _no_ipython):
        try:
            return ip(locals)
        except ImportError:
            pass


def _ipython(locals):
    from IPython import start_ipython
    start_ipython(argv=[], user_ns=locals)


def _ipython_pre_10(locals):  # pragma: no cover
    from IPython.frontend.terminal.ipapp import TerminalIPythonApp
    app = TerminalIPythonApp.instance()
    app.initialize(argv=[])
    app.shell.user_ns.update(locals)
    app.start()


def _ipython_terminal(locals):  # pragma: no cover
    from IPython.terminal import embed
    embed.TerminalInteractiveShell(user_ns=locals).mainloop()


def _ipython_010(locals):  # pragma: no cover
    from IPython.Shell import IPShell
    IPShell(argv=[], user_ns=locals).mainloop()


def _no_ipython(self):  # pragma: no cover
    raise ImportError('no suitable ipython found')


def invoke_default_shell(locals):
    try:
        import IPython  # noqa
    except ImportError:
        try:
            import bpython  # noqa
        except ImportError:
            return invoke_fallback_shell(locals)
        else:
            return invoke_bpython_shell(locals)
    else:
        return invoke_ipython_shell(locals)


@click.command(cls=CeleryCommand)
@click.option('-I',
              '--ipython',
              is_flag=True,
              cls=CeleryOption,
              help_group="Shell Options",
              help="Force IPython.")
@click.option('-B',
              '--bpython',
              is_flag=True,
              cls=CeleryOption,
              help_group="Shell Options",
              help="Force bpython.")
@click.option('--python',
              is_flag=True,
              cls=CeleryOption,
              help_group="Shell Options",
              help="Force default Python shell.")
@click.option('-T',
              '--without-tasks',
              is_flag=True,
              cls=CeleryOption,
              help_group="Shell Options",
              help="Don't add tasks to locals.")
@click.option('--eventlet',
              is_flag=True,
              cls=CeleryOption,
              help_group="Shell Options",
              help="Use eventlet.")
@click.option('--gevent',
              is_flag=True,
              cls=CeleryOption,
              help_group="Shell Options",
              help="Use gevent.")
@click.pass_context
def shell(ctx, ipython=False, bpython=False,
          python=False, without_tasks=False, eventlet=False,
          gevent=False):
    sys.path.insert(0, os.getcwd())
    if eventlet:
        import_module('celery.concurrency.eventlet')
    if gevent:
        import_module('celery.concurrency.gevent')
    import celery
    import celery.task.base
    app = ctx.obj.app
    app.loader.import_default_modules()

    # pylint: disable=attribute-defined-outside-init
    locals = {
        'app': app,
        'celery': app,
        'Task': celery.Task,
        'chord': celery.chord,
        'group': celery.group,
        'chain': celery.chain,
        'chunks': celery.chunks,
        'xmap': celery.xmap,
        'xstarmap': celery.xstarmap,
        'subtask': celery.subtask,
        'signature': celery.signature,
    }

    if not without_tasks:
        locals.update({
            task.__name__: task for task in app.tasks.values()
            if not task.name.startswith('celery.')
        })

    if python:
        return invoke_fallback_shell(locals)
    elif bpython:
        try:
            return invoke_bpython_shell(locals)
        except ImportError:
            ctx.obj.echo(f'{ctx.obj.ERROR}: bpython is not installed')
    elif ipython:
        try:
            return invoke_ipython_shell(locals)
        except ImportError as e:
            ctx.obj.echo(f'{ctx.obj.ERROR}: {e}')
    return invoke_default_shell(locals)