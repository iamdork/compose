import os
import contextlib
from helpers import notdefault, tru
import logging
import pkg_resources


@contextlib.contextmanager
def load(plugins):
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
        if os.path.isfile(f):
            execfile(os.path.expanduser(f), local)
        instance = local['Plugin'](environment.copy())
        instances.append(instance)
        environment.update(instance.environment())

    instances = filter(lambda i: i.initialize(), instances)

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

    yield instances

    for instance in instances:
        instance.cleanup()


class Plugin:
    """
    Interface definition for plugins that can interact with the docker-compose
    process.
    """

    def __init__(self, env):
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
    def project(self):
        return self.env['DORK_PROJECT']

    @property
    def instance(self):
        return self.env['DORK_INSTANCE']

    def info(self, project):
        return {}

    def preprocess_config(self, config):
        """
        Alter the docker-compose configuration object. The object is passed
        by reference.

        :type config: compose.config.config.Config
        """
        pass

    def initializing_volumes(self, volumes):
        """
        Act before volumes were initialized by docker-compose.

        :type volumes: list[compose.volume.Volume]
        """
        pass

    def removed_volumes(self, volumes):
        """
        Act after volumes are removed by docker-compose.

        :type volumes: list[compose.volume.Volume]
        """
        pass

    def initialized_networks(self, networks):
        """
        Act after networks are initialized by docker-compose.

        :type volumes: list[compose.network.Network]
        """
        pass

    def removing_networks(self, networks):
        """
        Act before networks are removed by docker-compose.

        :type volumes: list[compose.network.Network]
        """
        pass

    def building_service(self, service):
        """
        Alter a service before it will be built.
        :param service:
        :return:
        """
        pass

    def starting_service(self, service):
        """
        Alter a service before it will be started.
        :param service:
        :return:
        """
        pass

    def snapshot_save(self, snapshots=()):
        """
        Save the current volumes under the names provided.
        :type snapshots: list[str]
        """
        pass

    def snapshot_load(self, snapshots=()):
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

