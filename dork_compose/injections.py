import re

import os
from compose.cli.command import get_project
import compose.cli.command as cmd
from compose.cli.main import TopLevelCommand
from compose.config.config import load
from compose.config.environment import Environment
from compose.const import DEFAULT_TIMEOUT
from compose.project import Project
from compose.service import ConvergenceStrategy, BuildAction, Service
from dork_compose.helpers import tru

from functools import partial


def dork_config_load(plugins, config_details):
    config_data = load(config_details)
    for plugin in plugins:
        plugin.preprocess_config(config_data)
    return config_data


def get_dork_project(plugins, project_dir, config_path=None, project_name=None,
                     verbose=False, host=None, tls_config=None,
                     environment=None):

    cmd.config.load = partial(dork_config_load, plugins)
    project = get_project(project_dir, config_path, project_name, verbose, host, tls_config, environment)

    if 'COMPOSE_PROJECT_NAME' in os.environ:
        project.name = os.environ['COMPOSE_PROJECT_NAME']

    return DorkProject.from_project(project, plugins)


def get_dork_project_name(working_dir, project_name=None, environment=None):
    def normalize_name(name):
        # Full copy because compose strips dashes from project names.
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


class DorkTopLevelCommand(TopLevelCommand):
    __doc__ = TopLevelCommand.__doc__ + "\n".join([
        "  snapshot           Save or restore runtime data snapshots.",
        "      info               Display information about services."
    ])

    def __init__(self, project, project_dir='.'):
        super(DorkTopLevelCommand, self).__init__(project, project_dir)

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
        getattr(self.project, 'snapshot_' + options['COMMAND'])(options['SNAPSHOTS'])

    def info(self, options):
        """
        Display service status information.

        Usage: info
        """

        from terminaltables import AsciiTable
        rows = []

        for key, value in self.project.info().iteritems():
            rows.append([key + ':', value])

        table = AsciiTable(rows)
        table.outer_border = False
        table.inner_column_border = False
        table.inner_heading_row_border = False
        table.title = 'Dork status information'
        print table.table


class Pluggable(object):

    def set_plugins(self, plugins):
        self.__plugins = plugins

    @property
    def plugins(self):
        return self.__plugins


class DorkService(Service, Pluggable):

    @classmethod
    def from_service(cls, service, plugins=()):
        service.__class__ = cls
        service.set_plugins(plugins)
        return service

    def build(self, no_cache=False, pull=False, force_rm=False):
        for plugin in self.plugins:
            plugin.building(self)
        return super(DorkService, self).build(no_cache, pull, force_rm)


class DorkProject(Project, Pluggable):

    @classmethod
    def from_project(cls, project, plugins=()):
        project.__class__ = cls
        project.set_plugins(plugins)
        return project

    @classmethod
    def from_config(cls, name, config_data, client, plugins=()):
        project = super(DorkProject, cls).from_config(name, config_data, client)
        project.set_plugins(plugins)
        return project

    def get_services(self, service_names=None, include_deps=False):
        services = super(DorkProject, self).get_services(service_names, include_deps)
        return [DorkService.from_service(service, self.plugins) for service in services]

    def up(self, service_names=None, start_deps=True, strategy=ConvergenceStrategy.changed, do_build=BuildAction.none, timeout=DEFAULT_TIMEOUT, detached=False, remove_orphans=False):
        for plugin in self.plugins:
            plugin.initializing(self, service_names)

        containers = super(DorkProject, self).up(service_names, start_deps, strategy, do_build, timeout, detached, remove_orphans)

        for plugin in self.plugins:
            plugin.initialized(self, containers)

        for plugin in self.plugins:
            plugin.attach_auxiliary_project(self)

        return containers

    def down(self, remove_image_type, include_volumes, remove_orphans=False):
        for plugin in self.plugins:
            plugin.removing(self, include_volumes)

        for plugin in self.plugins:
            plugin.detach_auxiliary_project(self)

        super(DorkProject, self).down(remove_image_type, include_volumes, remove_orphans)

        for plugin in self.plugins:
            plugin.removed(self, include_volumes)

    def __snapshots(self):
        snapshots = []
        for plugin in self.plugins:
            snapshots.extend(plugin.snapshot_ls())
        return snapshots

    def snapshot_save(self, names=()):
        # If the provided names list is empty, collect plugins for
        # name suggestions from autosave plugins.
        if not names:
            names = filter(tru, [p.snapshot_autosave() for p in self.plugins])

        # Invoke plugin save hooks with collected names.
        self.stop()
        for plugin in self.plugins:
            plugin.snapshot_save(names)
        self.start()

    def snapshot_load(self, names=()):
        # If the names list is empty, collect most appropriate snapshots
        # from autoload plugins.
        if not names:
            names = filter(tru, [p.snapshot_autoload(self.__snapshots()) for p in self.plugins])

        # Iterate plugins from the right and stop when the first one
        # successfully loaded a snapshot.

        self.stop()
        for plugin in reversed(self.plugins):
            loaded = plugin.snapshot_load(names)
            if loaded:
                print(loaded)
                break

        self.start()

    def snapshot_rm(self, names=()):
        # If the names list is empty, collect most removable snapshots
        # from autoclean plugins.
        if not names:
            names = filter(tru, [p.snapshot_autoclean(self.__snapshots()) for p in self.plugins])

        for plugin in self.plugins:
            for removed in plugin.snapshot_rm(names):
                print(removed)

    def snapshot_ls(self, snapshots=()):
        for name in self.__snapshots():
            if not snapshots or name in snapshots:
                print(name)

    def info(self):
        info = {}
        for plugin in self.plugins:
            info.update(plugin.info(self))
        return info


