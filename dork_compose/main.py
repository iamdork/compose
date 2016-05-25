import os
from functools import partial


import plugin

import compose.config.config
import compose.project
import compose.cli.command
import compose.cli.main

from injections import DorkTopLevelCommand, get_dork_project

# Default plugins:
# env:   Read environment from .env files.
# lib:   Switch to dork library.
# multi: Assume single layer of multiple different projects.
# repo:  Turn on git auto snapshots.
# proxy: Run the proxy service.
DEFAULT_PLUGINS = 'env:lib:multi:git:filesystem:proxy:dbgp'


def run():
    with plugin.load(os.getenv('DORK_PLUGINS', DEFAULT_PLUGINS)) as plugins:

        # Replace compose TopLevelCommand with custom derivation.
        compose.cli.main.TopLevelCommand = DorkTopLevelCommand

        # Inject custom get_dork_project fu
        compose.cli.command.get_project = partial(get_dork_project, plugins)

        compose.cli.main.main()




