import os
from functools import partial


import plugin

import compose.config.config
import compose.config.validation
import compose.project
import compose.cli.command
import compose.cli.main

from injections import DorkTopLevelCommand, get_dork_project, get_dork_project_name, dork_config_load, dork_validate_against_config_schema, dork_validate_service_constraints
from compose.config.environment import env_vars_from_file

# Default plugins:
# lib:   Switch to dork library.
# multi: Assume single layer of multiple different projects.
# repo:  Turn on git auto snapshots.
# proxy: Run the proxy service.
DEFAULT_PLUGINS = 'env:multi:lib:autobuild:hotcode:dependencies:git:filesystem:proxy:dns:vault:cleanup:tracker'


def run():

    with plugin.load(os.getenv('DORK_PLUGINS', DEFAULT_PLUGINS)) as plugins:

        # Override all occurences of config schema related functions.
        compose.config.config.validate_against_config_schema = partial(dork_validate_against_config_schema, plugins)
        compose.config.validate_service_constraints = partial(dork_validate_service_constraints, plugins)
        compose.config.config.validate_service_constraints = partial(dork_validate_service_constraints, plugins)

        # Inject configuration hooks.
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




