import os
from functools import partial


import plugin

import compose.config.config
import compose.project
import compose.cli.command
import compose.cli.main

from injections import DorkTopLevelCommand, get_dork_project, get_dork_project_name, dork_config_load, DorkNetworks
from compose.config.environment import env_vars_from_file

# Default plugins:
# lib:   Switch to dork library.
# multi: Assume single layer of multiple different projects.
# repo:  Turn on git auto snapshots.
# proxy: Run the proxy service.
DEFAULT_PLUGINS = 'multi:lib:hotcode:git:filesystem:proxy'


def update_environment():
    # Collect separate environment dict from .env files in
    # current and parent directories.
    path = filter(len, os.path.abspath(os.path.curdir).split('/'))
    current = ''
    env = {}
    env.update(os.environ)

    while len(path):
        current = current + '/' + path.pop(0)
        envfile = '%s/.dork.env' % current
        if os.path.isfile(envfile):
            for key, value in env_vars_from_file(envfile).iteritems():
                os.environ[key] = os.path.expandvars(value)
            continue
        envfile = '%s/.env' % current
        if os.path.isfile(envfile):
            for key, value in env_vars_from_file(envfile).iteritems():
                os.environ[key] = os.path.expandvars(value)

    os.environ.update(env)

    if 'DORK_PLUGINS' not in os.environ:
        os.environ['DORK_PLUGINS'] = DEFAULT_PLUGINS


def run():
    # Apply environment variables from .env files.
    update_environment()

    with plugin.load(os.getenv('DORK_PLUGINS', DEFAULT_PLUGINS)) as plugins:

        compose.config.config.load = partial(dork_config_load, plugins)

        # Replace compose TopLevelCommand with custom derivation with additional
        # commands.
        compose.cli.main.TopLevelCommand = DorkTopLevelCommand

        # Inject custom get_dork_project to replace instances with DorkProjects.
        compose.cli.command.get_project = partial(get_dork_project, plugins)

        # Inject custom project_name function to allow dashes in project names.
        compose.cli.command.get_project_name = get_dork_project_name

        # Run the original dork-compose main function.
        compose.cli.main.main()




