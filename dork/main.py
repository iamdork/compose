import os
import re

from compose.cli.main import TopLevelCommand
from compose.service import Service
from compose.volume import ProjectVolumes
from compose.network import ProjectNetworks
from compose.config.config import Config
from compose.config.environment import Environment

from helpers import tru, notdefault

import plugin

import compose.config.config
import compose.project
import compose.cli.command
import compose.cli.main

# Default plugins:
# env:   Read environment from .env files.
# lib:   Switch to dork library.
# multi: Assume single layer of multiple different projects.
# repo:  Turn on git auto snapshots.
# proxy: Run the proxy service.
DEFAULT_PLUGINS = 'env:lib:multi:git:filesystem:proxy'


def run():
    with plugin.load(os.getenv('DORK_PLUGINS', DEFAULT_PLUGINS)) as plugins:

        class DorkTopLevelCommand(TopLevelCommand):
            __doc__ = TopLevelCommand.__doc__ + "\n".join([
                "  snapshot           Save or restore runtime data snapshots.",
                "      info               Display information about services."
            ])

            def __init__(self, project, project_dir='.'):
                print('lala')
                super(DorkTopLevelCommand, self).__init__(project, project_dir)

            def __snapshots(self):
                snapshots = []
                for plugin in plugins:
                    snapshots.extend(plugin.snapshot_ls())
                return snapshots

            def snapshot(self, options):
                """
                Save or restore volume snapshots.
                Usage: snapshot COMMAND [SNAPSHOTS...]

                Commands:
                  save   Store volumes state as snapshot.
                  load   Load the closest snapshot or a specific one.
                  ls     List all available snapshots.
                  rm     Clean up snapshots or remove a specific one.
                """
                getattr(self, '_snapshot_' + options['COMMAND'])(options['SNAPSHOTS'])

            def info(self, options):
                """
                Display service status information.

                Usage: info
                """
                from terminaltables import AsciiTable
                rows = []

                for plugin in plugins:
                    for key, value in plugin.info().iteritems():
                        rows.append([key + ':', value])

                table = AsciiTable(rows)
                table.outer_border = False
                table.inner_column_border = False
                table.inner_heading_row_border = False
                table.title = 'Dork status information'
                print table.table

            def _snapshot_save(self, names=()):
                # If the provided names list is empty, collect plugins for
                # name suggestions from autosave plugins.
                if not names:
                    names = filter(tru, [p.snapshot_autosave() for p in plugins])

                # Invoke plugin save hooks with collected names.
                for plugin in plugins:
                    plugin.snapshot_save(names)

            def _snapshot_load(self, names=()):
                # If the names list is empty, collect most appropriate snapshots
                # from autoload plugins.
                if not names:
                    names = filter(tru, [p.snapshot_autoload(self.__snapshots()) for p in plugins])

                # Iterate plugins from the right and stop when the first one
                # successfully loaded a snapshot.

                self.project.stop()
                for plugin in reversed(plugins):
                    loaded = plugin.snapshot_load(names)
                    if loaded:
                        print(loaded)
                        break

                self.project.start()

            def _snapshot_rm(self, names=()):
                # If the names list is empty, collect most removable snapshots
                # from autoclean plugins.
                if not names:
                    names = filter(tru, [p.snapshot_autoclean(self.__snapshots()) for p in plugins])

                for plugin in plugins:
                    for removed in plugin.snapshot_rm(names):
                        print(removed)

            def _snapshot_ls(self, snapshots=()):
                for name in self.__snapshots():
                    if not snapshots or name in snapshots:
                        print(name)

        class DorkService(Service):
            def build(self, no_cache=False, pull=False, force_rm=False):
                for plugin in plugins:
                    plugin.building_service(self)
                return super(DorkService, self).build(no_cache, pull, force_rm)

        class DorkProjectVolumes(ProjectVolumes):

            def initialize(self):
                for plugin in plugins:
                    plugin.initializing_volumes(self.volumes)
                return super(DorkProjectVolumes, self).initialize()

            def remove(self):
                super(DorkProjectVolumes, self).remove()
                for plugin in plugins:
                    plugin.removed_volumes(self.volumes)

        class DorkProjectNetworks(ProjectNetworks):

            def initialize(self):
                super(DorkProjectNetworks, self).initialize()
                for plugin in plugins:
                    plugin.initialized_networks(self.networks)

            def remove(self):
                for plugin in plugins:
                    plugin.removing_networks(self.networks)
                super(DorkProjectNetworks, self).remove()

        class DorkConfig(Config):
            def __init__(self, *args, **kwargs):
                super(DorkConfig, self).__init__(self, *args, **kwargs)
                for plugin in plugins:
                    plugin.preprocess_config(self)

        # Full copy of compose.command.cli.get_project_name
        # required because normalize does not allow dashes.
        def get_dork_project_name(working_dir, project_name=None, environment=None):

            def normalize_name(name):
                # only this part is overridden
                return re.sub(r'[^a-z0-9\-]', '', name.lower())

            if not environment:
                environment = Environment.from_env_file(working_dir)
            project_name = project_name or environment.get('COMPOSE_PROJECT_NAME')
            if project_name:
                return normalize_name(project_name)

            project = os.path.basename(os.path.abspath(working_dir))
            if project:
                return normalize_name(project)

            return 'default'

        # Replace compose TopLevelCommand with custom derivation.
        compose.cli.main.TopLevelCommand = DorkTopLevelCommand

        # Inject our own service derivation to get lifecycle hooks.
        compose.project.Service = DorkService

        # Replace the network controller to inject proxy updates.
        compose.project.ProjectNetworks = DorkProjectNetworks

        # Replace the volume controller to inject volume plugin initiation
        # lifecycle.
        compose.project.ProjectVolumes = DorkProjectVolumes

        # Replace config class to allow alteration.
        compose.config.config.Config = DorkConfig

        # Replace get_project_name function to allow dashes in container names.
        compose.cli.command.get_project_name = get_dork_project_name

        # Run original docker compose main function.
        compose.cli.main.main()
