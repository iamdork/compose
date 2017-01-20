import os
import contextlib

from compose.cli.command import get_client
from compose.cli.docker_client import docker_client
from compose.config import config
from compose.config.environment import Environment
from dork_compose.injections import dork_config_load
from compose.const import API_VERSIONS
from compose.project import Project
from helpers import notdefault, tru
import pkg_resources
import filelock

import logging
log = logging.getLogger(__name__)


@contextlib.contextmanager
def load(plugins, command):
    instances = []

    environment = {
        'DORK_PROJECT': 'default',
        'DORK_INSTANCE': 'default',
        'DORK_SOURCE': os.path.abspath(os.curdir),
        'DORK_DATA_DIR': '~/.dork',
    }
    environment.update(os.environ)

    for plugin in plugins.split(':'):
        local = {}
        if '=' in plugin:
            (plugin, f) = plugin.split('=')
        else:
            f = "%s/%s.py" % (pkg_resources.resource_filename('dork_compose', 'plugins'), plugin)

        f = os.path.expanduser(f)

        try:
            execfile(os.path.expanduser(f), local)
            instances.append(local['Plugin'](environment.copy(), plugin, command))
            environment.update(instances[-1].environment())

            log.debug('Loaded plugin %s.' % plugin)
        except Exception as ex:
            log.warning('Could not load plugin %s: %s' % (plugin, ex))
            pass

    # If there is no explicit project name in the environment, set
    # [project]--[instance]
    if 'COMPOSE_PROJECT_NAME' not in environment:
        parts = filter(tru, [
            notdefault(environment['DORK_PROJECT']),
            notdefault(environment['DORK_INSTANCE'])
        ])
        if parts:
            environment.update({
                'COMPOSE_PROJECT_NAME': '--'.join(parts)
            })

    os.environ.update(environment)

    try:
        yield instances
    finally:
        for instance in instances:
            instance.cleanup()


class Plugin(object):
    """
    Interface definition for plugins that can interact with the docker-compose
    process.
    """

    def __init__(self, env, name, command):
        self.name = name
        self.env = env.copy()
        self.log = logging.getLogger(__name__)

    def initialize(self):
        return True

    def cleanup(self):
        pass

    def environment(self):
        return {}

    @property
    def basedir(self):
        return self.env['DORK_SOURCE']

    @property
    def datadir(self):
        return os.path.expanduser(self.env['DORK_DATA_DIR'])

    @property
    def lockdir(self):
        return '%s/locks' % self.datadir

    @property
    def project(self):
        return self.env['DORK_PROJECT']

    @property
    def instance(self):
        return self.env['DORK_INSTANCE']

    def info(self, project):
        return {}

    def alter_config_schema(self, schema):
        pass

    def preprocess_config(self, config):
        """
        Alter the docker-compose configuration object. The object is passed
        by reference.

        :type config: compose.config.config.Config
        """
        pass

    def building(self, service, no_cache, pull, force_rm):
        pass

    def after_build(self, service, no_cache, pull, force_rm):
        pass

    def initializing(self, project, service_names=None):
        pass

    def creating_container(self, service):
        pass

    def starting_container(self, container):
        pass

    def initialized(self, project, containers=None):
        pass

    def removing(self, project, include_volumes=False):
        pass

    def removed(self, project, include_volumes=False):
        pass

    def snapshot_save(self, snapshots=(), volumes=()):
        """
        Save the current volumes under the names provided.
        :type snapshots: list[str]
        """
        pass

    def snapshot_load(self, snapshots=(), volumes=()):
        """
        Try to load the snapshots provided. If multiple snapshots are requested
        the last valid one should be used.
        Returns the id of the snapshot loaded.

        :type snapshots: list[str]
        :rtype: str
        """
        pass

    def snapshot_rm(self, snapshots=()):
        """
        Remove the list of snapshots. Invalid snapshots are silently ignored.
        Return a list of snapshot id's that actually have been removed.

        :type snapshots: list[str]
        :rtype: list[str]
        """
        return []

    def snapshot_ls(self):
        """
        List available snapshots. I the snapshots parameter is provided, reduce
        check for existence of these and return the narrowed list.

        :rtype: list[str]
        """
        return []

    def snapshot_autosave(self):
        """
        Choose an automatic name for the next snapshot.

        :rtype: str
        """
        return None

    def snapshot_autoload(self, snapshots=()):
        """
        Choose the most appropriate snapshot to be loaded from the list provided.
        If no snapshot applies, return [None].

        :type snapshots: list[str]
        :rtype: str
        """
        return None

    def snapshot_autoclean(self, snapshots=()):
        """
        Decide which snapshots in the list can be cleaned up safely, without
        loosing information.

        :type snapshots: list[str]
        :rtype: list[str]
        """
        return []

    @property
    def auxiliary_project(self):
        return None

    @property
    def auxiliary_project_name(self):
        return 'dork_aux_%s' % self.name

    def attach_auxiliary_project(self, network):
        if not self.auxiliary_project:
            return

        aux = self.get_auxiliary_project()

        if not os.path.exists(self.lockdir):
            os.makedirs(self.lockdir)
        lock = filelock.FileLock("%s/%s" % (self.lockdir, self.auxiliary_project_name))

        with lock.acquire(60):
            aux.up(detached=True, remove_orphans=True)

            client = docker_client(self.environment())

            containers = client.containers(filters={
                'label': [
                    'org.iamdork.auxiliary',
                    'com.docker.compose.project=%s' % self.auxiliary_project_name
                ],
            })

            for container in containers:
                if network not in container['NetworkSettings']['Networks']:
                    client.connect_container_to_network(container, network)

    def detach_auxiliary_project(self, network):
        if not self.auxiliary_project:
            return

        aux = self.get_auxiliary_project()

        if not os.path.exists(self.lockdir):
            os.makedirs(self.lockdir)
        lock = filelock.FileLock("%s/%s" % (self.lockdir, self.auxiliary_project_name))

        with lock.acquire(60):

            client = docker_client(self.environment())

            containers = client.containers(filters={
                'label': [
                    'org.iamdork.auxiliary',
                    'com.docker.compose.project=%s' % self.auxiliary_project_name
                ],
            })

            for container in containers:
                if network in container['NetworkSettings']['Networks']:
                    if (len(container['NetworkSettings']['Networks']) - 1) == len(aux.networks.networks):
                        aux.down(remove_image_type=None, include_volumes=False, remove_orphans=True)
                        break
                    else:
                        client.disconnect_container_from_network(container, network)

    def get_auxiliary_project(self):
        config_details = config.find(self.auxiliary_project, [], Environment(self.environment()))
        project_name = self.auxiliary_project_name
        config_data = dork_config_load([], config_details)

        client = get_client(self.environment(), version=API_VERSIONS[config_data.version])

        return Project.from_config(project_name, config_data, client)
