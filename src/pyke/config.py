''' Loads configuration (pyke-config.json) files.'''

import json
from pathlib import Path

from .utilities import MalformedConfigError, ensure_list

class Configurator:
    ''' Loads configuration jsons.'''

    def __init__(self):
        self.loaded_configs: list[Path] = []
        self.argument_aliases = {}
        self.action_aliases = {}
        self.default_action = ''
        self.default_arguments = []
        self.cache_makefile_module = False

    def report(self):
        ''' Prints the current configuration. '''
        report = 'Loaded configuration files:\n'
        for file in self.loaded_configs:
            report += f'    {file}\n'
        report += 'Argument aliases:\n'
        for k, v in self.argument_aliases.items():
            report += f'    {k}:\n'
            for i in v:
                report += f'        {i}\n'
        report += 'Action aliases:\n'
        for k, v in self.action_aliases.items():
            report += f'    {k}:\n'
            for i in v:
                report += f'        {i}\n'
        report += f'Default action: {self.default_action}\nDefault arguments:\n'
        for arg in self.default_arguments:
            report += f'    {arg}\n'
        report += f'Caching makefile modules: {self.cache_makefile_module}\n'
        return report

    def load_from_default_config(self):
        ''' Sets the default config options.'''
        file = Path(__file__).parent / 'pyke-config.json'
        if file.exists():
            self.load_config_file(file)

    def load_from_home_config(self):
        ''' Loads config from ~/.config/pyke/pyke-config.json. '''
        file = Path.home() / '.config' / 'pyke' / 'pyke-config.json'
        if file.exists():
            self.load_config_file(file)

    def load_from_makefile_dir(self, make_dir: Path):
        ''' Loads config from standard files.'''
        file = Path(make_dir) / 'pyke-config.json'
        if file.exists():
            self.load_config_file(file)

    def load_config_file(self, file: Path):
        ''' Open a file for processing.'''
        if file in self.loaded_configs:
            return

        self.loaded_configs.append(file)
        try:
            with open(file, 'r', encoding='utf-8') as fi:
                config = json.load(fi)
                self.process_config(file, config)
        except (FileNotFoundError, MalformedConfigError) as e:
            if e is FileNotFoundError:
                print (f'Could not find config file "{file}".')
            elif e is MalformedConfigError:
                print (f'Malformed config file "{file}".')
            else:
                print (f'{e}')

    def process_config(self, path: Path | None, config: str):
        ''' Processes a json config string.'''
        if not isinstance(config, dict):
            raise MalformedConfigError(f'Config file {path}: Must be a JSON dictonary.')

        def read_block(config, subblock, keyname) -> dict[str, list[str]]:
            rets = {}
            if aliases := config.get(subblock):
                if not isinstance(aliases, dict):
                    raise MalformedConfigError(
                        f'Config file {path}: "{subblock}" must be a dictionary.')
                for alias, values in aliases.items():
                    if not isinstance(alias, str):
                        raise MalformedConfigError(
                            f'Config file {path}: "{config}/{keyname}" key must be a string.')
                    if isinstance(values, str):
                        values = [values]
                    if (not isinstance(values, list) or
                        any(not isinstance(value, str) for value in values)):
                        raise MalformedConfigError(
                            f'Config file {path}: "{config}/{keyname}" value must be a string '
                            'or a list of strings.')
                    rets[alias] = values
            return rets

        if includes := config.get('include', []):
            includes = ensure_list(includes)
            for inc in includes:
                if path and not str(inc).startswith('/'):
                    inc = path.parent / inc
                self.load_config_file(inc)

        self.argument_aliases |= read_block(config, 'argument_aliases', 'argument')
        self.action_aliases |= read_block(config, 'action_aliases', 'action')
        if default_action := config.get('default_action'):
            if not isinstance(default_action, str):
                raise MalformedConfigError(
                    f'Config file {path}: "default_action" must be a string.')
            self.default_action = default_action
        if default_arguments := config.get('default_arguments'):
            if not isinstance(default_arguments, list):
                raise MalformedConfigError(
                    f' Config file {path}: "default_arguments" must be a list of strings.')
            self.default_arguments.extend(default_arguments)
        if cache_makefile_module := config.get('cache_makefile_module', False):
            if not isinstance(cache_makefile_module, bool):
                raise MalformedConfigError(
                    f' Config file {path}: "cache_makefile_module" must be a boolean.')
            self.cache_makefile_module = cache_makefile_module
