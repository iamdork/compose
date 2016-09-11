import dork_compose.plugin
import os
import shutil

import time
from compose.config.config import VolumeSpec
from docker.client import from_env
from docker.errors import APIError


class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name):
        dork_compose.plugin.Plugin.__init__(self, env, name)
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
        client = from_env()
        for name in snapshots:

            snapshot = '%s/%s' % (self.snapshot, name)

            for v in volumes:
                try:
                    client.inspect_image('iamdork/rsync')
                except APIError:
                    client.pull('iamdork/rsync')

                sync = client.create_container(
                    image='iamdork/rsync',
                    volumes=['/destination', '/source'],
                    host_config=client.create_host_config(binds=[
                        '%s/%s:/destination' % (snapshot, v),
                        '%s:/source' % volumes[v].full_name
                    ]),
                )

                client.start(sync)
                while client.inspect_container(sync)['State']['Running']:
                    time.sleep(0.1)

    def snapshot_load(self, snapshots=(), volumes=()):
        options = list(set(self.snapshot_ls()) & set(snapshots))
        client = from_env()
        if len(options):
            name = options[-1]

            snapshot = '%s/%s' % (self.snapshot, name)

            for v in volumes:
                try:
                    client.inspect_image('iamdork/rsync')
                except APIError:
                    client.pull('iamdork/rsync')

                sync = client.create_container(
                    image='iamdork/rsync',
                    volumes=['/destination', '/source'],
                    host_config=client.create_host_config(binds=[
                        '%s/%s:/source' % (snapshot, v),
                        '%s:/destination' % volumes[v].full_name
                    ]),
                )

                client.start(sync)
                while client.inspect_container(sync)['State']['Running']:
                    time.sleep(0.1)
                return name
        return None

    def snapshot_rm(self, snapshots=()):
        for name in snapshots:
            snapshot = '%s/%s' % (self.snapshot, name)
            # Remove the current snapshot, if one exists.
            if os.path.exists(snapshot):
                shutil.rmtree(snapshot)
                yield name

    def snapshot_ls(self):
        return [path for path in os.listdir(self.snapshot)]


