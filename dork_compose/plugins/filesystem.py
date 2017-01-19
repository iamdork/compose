import dork_compose.plugin
import os

import time
from docker.api.client import APIClient
from docker.errors import APIError


import logging
log = logging.getLogger(__name__)

class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name, command):
        dork_compose.plugin.Plugin.__init__(self, env, name, command)
        self.__mkdir(self.snapshots)
        self.__mkdir(self.volumes)

    @property
    def volumes(self):
        return os.path.expanduser(self.env.get('DORK_FILESYSTEM_VOLUME_PATH', '%s/volumes' % self.datadir))

    @property
    def volume(self):
        return '%s/%s/%s' % (
            os.path.expanduser(self.volumes),
            self.project,
            self.instance
        )

    @property
    def snapshots(self):
        return os.path.expanduser(self.env.get('DORK_FILESYSTEM_SNAPSHOT_PATH', '%s/snapshots' % self.datadir))

    @property
    def snapshot(self):
        return '%s/%s' % (os.path.expanduser(self.snapshots), self.project)

    def __mkdir(self, dir):
        if not os.path.exists(dir):
            os.makedirs(dir)

    def snapshot_save(self, snapshots=(), volumes=()):
        client = APIClient()
        for name in snapshots:

            snapshot = '%s/%s' % (self.snapshot, name)

            for v in volumes:
                log.info("Saving volume %s to %s/%s." % (v, snapshot, v))
                try:
                    client.inspect_image('iamdork/rsync')
                except APIError:
                    client.pull('iamdork/rsync')

                sync = client.create_container(
                    image='iamdork/rsync',
                    volumes=['/destination', '/source'],
                    cpu_shares=256,
                    host_config=client.create_host_config(binds=[
                        '%s/%s:/destination' % (snapshot, v),
                        '%s:/source' % volumes[v].full_name
                    ]),
                )

                try:
                    client.start(sync)
                    while client.inspect_container(sync)['State']['Running']:
                        time.sleep(0.5)
                finally:
                    client.remove_container(sync)

    def snapshot_load(self, snapshots=(), volumes=()):
        options = list(set(self.snapshot_ls()) & set(snapshots))
        client = APIClient()
        try:
            client.inspect_image('iamdork/rsync')
        except APIError:
            client.pull('iamdork/rsync')
        if len(options):
            name = options[-1]

            snapshot = '%s/%s' % (self.snapshot, name)
            if not os.path.isdir(snapshot):
                log.error("Snapshot %s of project %s doesn't exist." % (name, self.project))
                return

            for v in volumes:
                log.info("Restoring volume %s from %s/%s." % (v, snapshot, v))
                sync = client.create_container(
                    image='iamdork/rsync',
                    volumes=['/destination', '/source'],
                    host_config=client.create_host_config(binds=[
                        '%s/%s:/source' % (snapshot, v),
                        '%s:/destination' % volumes[v].full_name
                    ]),
                )

                try:
                    client.start(sync)
                    while client.inspect_container(sync)['State']['Running']:
                        time.sleep(0.5)
                finally:
                    client.remove_container(sync)
            return name
        return None

    def snapshot_rm(self, snapshots=()):
        client = APIClient()
        try:
            client.inspect_image('alpine:3.4')
        except APIError:
            client.pull('alpine:3.4')
        for name in snapshots:
            snapshot = '%s/%s' % (self.snapshot, name)
            if not os.path.isdir(snapshot):
                log.error("Snapshot %s of project %s doesn't exist." % (name, self.project))
                continue

            container = client.create_container(
                command='rm -rf /snapshots/%s' % name,
                image='alpine:3.4',
                volumes=['/snapshots'],
                host_config=client.create_host_config(binds=[
                    '%s:/snapshots' % self.snapshot,
                ]),
            )

            try:
                client.start(container)
                while client.inspect_container(container)['State']['Running']:
                    time.sleep(0.5)
            finally:
                client.remove_container(container)
            yield name

    def snapshot_ls(self):
        return [path for path in os.listdir(self.snapshot)]


