import inspect
import sys
import json
import os
import pprint
import runpy

from .log import conf_log
from .registry import PluginBase, bind
from .utils import dict_generator


def print_registry():
    # monkey patch sorting
    pprint._safe_key.__lt__ = lambda x, y: True

    reg = pprint.pformat(PluginBase.registry)
    conf_log().info(f'Registry settings:\n{reg}')


class RCSettings:
    def __init__(self, rc_fn):
        self.rc_fn = rc_fn
        search_dirs = self.find_seach_dirs()
        unique_search_dirs = list(dict.fromkeys(search_dirs))
        for path in reversed(unique_search_dirs):
            self.find_rc(path)

    def find_seach_dirs(self):
        search_dirs = []
        home_path = os.environ.get('HOME')

        if hasattr(sys.modules['__main__'], '__file__'):
            filename = sys.modules['__main__'].__file__
        else:
            # conf_log().warning(
            #     'Searching for .py files: main does not have __file__, inspecting stack instead'
            # )
            _, filename, _, _, _, _ = inspect.stack()[-1]
        dirname = os.path.dirname(filename)
        search_dirs.append(dirname)

        if home_path is not None:
            while dirname not in ('/', home_path):
                dirname = os.path.abspath(os.path.join(dirname, '..'))
                search_dirs.append(dirname)

            search_dirs.append(home_path)
            search_dirs.append(os.path.join(home_path, '.pygears'))

        return search_dirs

    def find_rc(self, dirname):
        rc_path = os.path.join(dirname, f'{self.rc_fn}.py')
        if os.path.exists(rc_path):
            runpy.run_path(rc_path)
            return

        conf = None
        rc_path = os.path.join(dirname, f'{self.rc_fn}.yaml')
        if os.path.exists(rc_path):
            with open(rc_path) as f:
                try:
                    import yaml
                    conf = yaml.safe_load(f)
                except ImportError:
                    conf_log().warning(
                        f'PyGears YAML configuration file found'
                        f'at "{rc_path}", but yaml python package not '
                        f'installed')

        rc_path = os.path.join(dirname, f'{self.rc_fn}.json')
        if os.path.exists(rc_path):
            with open(rc_path) as f:
                conf = json.load(f)

        if conf:
            for c_list in dict_generator(conf):
                keys = '/'.join([str(x) for x in c_list[:-1]])
                bind(keys, c_list[-1])
