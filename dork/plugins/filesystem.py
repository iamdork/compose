import dork.plugin
import os
import shutil
from compose.config.config import VolumeSpec


class Plugin(dork.plugin.Plugin):

    @property
    def volumes(self):
        return self.env.get('DORK_FILESYSTEM_VOLUME_PATH', '/var/dork/volumes')

    @property
    def volume(self):
        return '%s/%s/%s' % (
            os.path.expanduser(self.volumes),
            self.project,
            self.instance
        )

    @property
    def snapshots(self):
        return self.env.get('DORK_FILESYSTEM_SNAPSHOT_PATH', '/var/dork/snapshots')

    @property
    def snapshot(self):
        return '%s/%s' % (os.path.expanduser(self.snapshots), self.project)

    def __mkdir(self, dir):
        if not os.path.exists(dir):
            os.makedirs(dir)

    def preprocess_config(self, config):
        for service in config.services:
            if 'volumes' in service:
                for index, volume in enumerate(service['volumes']):
                    if volume.is_named_volume:
                        service['volumes'][index] = VolumeSpec.parse('%s/%s:%s' % (
                            self.volume,
                            volume.external,
                            volume.internal
                        ))

        for key in config.volumes.keys():
            del config.volumes[key]

    def initialize_volumes(self, volumes):
        self.__mkdir(self.snapshots)
        self.__mkdir(self.volumes)

    def remove_volumes(self, volumes):
        shutil.rmtree(self.volumes)

    def snapshot_save(self, snapshots=()):
        for name in snapshots:
            snapshot = '%s/%s' % (self.snapshots, name)
            # Remove the current snapshot, if one exists.
            shutil.rmtree(snapshot, ignore_errors=True)
            # Copy the volumes directory to the
            shutil.copytree(self.volume, snapshot)

    def snapshot_load(self, snapshots=()):
        options = set(self.snapshot_ls()) & set(snapshots)
        if len(options):
            name = options[-1]
            snapshot = '%s/%s' % (self.snapshots, name)
            # Remove the current volume directory.
            shutil.rmtree(self.volume, ignore_errors=True)
            # Copy the snapshot as new volume.
            shutil.copytree(snapshot, self.volume)
            return name
        return None

    def snapshot_rm(self, snapshots=()):
        for name in snapshots:
            snapshot = '%s/%s' % (self.snapshots, name)
            # Remove the current snapshot, if one exists.
            if os.path.exists(snapshot):
                shutil.rmtree(snapshot)
                yield snapshot

    def snapshot_ls(self):
        return [path for path in os.listdir(self.snapshots)]


