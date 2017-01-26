import re

import os
from compose.cli.command import get_project
import compose.cli.command as cmd
from compose.cli.main import TopLevelCommand, perform_command
from compose.cli.utils import get_version_info
from compose.config.config import load
from compose.config.environment import Environment
from compose.const import DEFAULT_TIMEOUT
from compose.project import Project, ProjectNetworks
from compose.service import ConvergenceStrategy, BuildAction, Service
from compose.config.validation import load_jsonschema, get_resolver_path, \
    handle_errors, process_config_schema_errors, \
    process_service_constraint_errors
from dork_compose.helpers import tru

from functools import partial

from jsonschema import Draft4Validator
from jsonschema import FormatChecker
from jsonschema import RefResolver
import dork_compose


import logging
log = logging.getLogger(__name__)


def dork_get_version_info(scope):
    return '%s%sdork-compose version %s, build %s ' % (
        get_version_info(scope),
        ', ' if scope == 'compose' else '\n',
        dork_compose.__version__,
        dork_get_build_version()
    )


def dork_get_build_version():
    filename = os.path.join(os.path.dirname(dork_compose.__file__), 'GITSHA')
    if not os.path.exists(filename):
        return 'unknown'
    with open(filename) as fh:
        return fh.read().strip()


def dork_perform_command(options, handler, command_options):
    if '--timeout' in options and not options['--timeout']:
        options['--timeout'] = os.environ.get('DORK_DEFAULT_TIMEOUT', DEFAULT_TIMEOUT)
    return perform_command(options, handler, command_options)


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


def dork_validate_service_constraints(plugins, config, service_name, version):
    def handler(errors):
        return process_service_constraint_errors(errors, service_name, version)
    schema = load_jsonschema(version)

    for plugin in plugins:
        plugin.alter_config_schema(schema)

    validator = Draft4Validator(schema['definitions']['constraints']['service'])
    handle_errors(validator.iter_errors(config), handler, None)


def dork_validate_against_config_schema(plugins, config_file):
    schema = load_jsonschema(config_file.version)
    for plugin in plugins:
        plugin.alter_config_schema(schema)
    format_checker = FormatChecker(["ports", "expose"])
    validator = Draft4Validator(
        schema,
        # TODO: wait for fix in docker-compose
        # docker-compose does not append filename, therefore caches
        # always miss.
        resolver=RefResolver(get_resolver_path() + "config_schema_v{0}.json".format(config_file.version), schema),
        format_checker=format_checker)
    handle_errors(
        validator.iter_errors(config_file.config),
        process_config_schema_errors,
        config_file.filename)


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
            plugin.building(self, no_cache, pull, force_rm)

        result = super(DorkService, self).build(no_cache, pull, force_rm)

        for plugin in self.plugins:
            plugin.after_build(self, no_cache, pull, force_rm)

        return result

    def start_container(self, container):
        for plugin in self.plugins:
            plugin.starting_container(container)
        return super(DorkService, self).start_container(container)

    def create_container(self, one_off=False, previous_container=None,
                         number=None, quiet=False, **override_options):

        for plugin in self.plugins:
            plugin.creating_container(self)
        return super(DorkService, self).create_container(one_off,
                                                         previous_container,
                                                         number, quiet,
                                                         **override_options)


class DorkNetworks(ProjectNetworks, Pluggable):
    def initialize(self):
        super(DorkNetworks, self).initialize()

        for key, network in self.networks.iteritems():
            for plugin in self.plugins:
                plugin.attach_auxiliary_project(network.full_name)

    def remove(self):
        for key, network in self.networks.iteritems():
            for plugin in self.plugins:
                plugin.detach_auxiliary_project(network.full_name)

        super(DorkNetworks, self).remove()


class DorkProject(Project, Pluggable):

    @classmethod
    def from_project(cls, project, plugins=()):
        project.__class__ = cls
        project.set_plugins(plugins)
        project.networks.__class__ = DorkNetworks
        project.networks.set_plugins(plugins)
        return project

    @classmethod
    def from_config(cls, name, config_data, client, plugins=()):
        project = super(DorkProject, cls).from_config(name, config_data, client)
        project.set_plugins(plugins)
        project.networks.set_plugins(plugins)
        return project

    def get_service(self, name):
        return DorkService.from_service(super(DorkProject, self).get_service(name), self.plugins)

    def up(self, service_names=None, start_deps=True, strategy=ConvergenceStrategy.changed, do_build=BuildAction.none, timeout=DEFAULT_TIMEOUT, detached=False, remove_orphans=False):
        for plugin in self.plugins:
            plugin.initializing(self, service_names)

        containers = super(DorkProject, self).up(service_names, start_deps, strategy, do_build, timeout, detached, remove_orphans)

        for plugin in self.plugins:
            plugin.initialized(self, containers)

        return containers

    def down(self, remove_image_type, include_volumes, remove_orphans=False):
        for plugin in self.plugins:
            plugin.removing(self, include_volumes)

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
            plugin.snapshot_save(names, self.volumes.volumes)
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
            loaded = plugin.snapshot_load(names, self.volumes.volumes)
            if loaded:
                log.info("Loaded snapshot %s through plugin %s." % (loaded, plugin.name))
                break
        self.start()

    def snapshot_rm(self, names=()):
        # If the names list is empty, collect most removable snapshots
        # from autoclean plugins.
        if not names:
            names = filter(tru, [p.snapshot_autoclean(self.__snapshots()) for p in self.plugins])

        for plugin in self.plugins:
            for removed in plugin.snapshot_rm(names):
                log.info("Removed snapshot %s through plugin %s." % (removed, plugin.name))

    def snapshot_ls(self, snapshots=()):
        for name in self.__snapshots():
            if not snapshots or name in snapshots:
                log.info(name)

    def info(self):
        info = {}
        for plugin in self.plugins:
            info.update(plugin.info(self))
        return info


