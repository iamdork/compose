import dork_compose.plugin
import os
import shutil
from compose.config.config import VolumeSpec


class Plugin(dork_compose.plugin.Plugin):

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

    def initializing_volumes(self, volumes):
        self.__mkdir(self.snapshots)
        self.__mkdir(self.volumes)

    def removed_volumes(self, volumes):
        shutil.rmtree(self.volumes, ignore_errors=True)

    def snapshot_save(self, snapshots=()):
        for name in snapshots:
            snapshot = '%s/%s' % (self.snapshot, name)
            # Remove the current snapshot, if one exists.
            shutil.rmtree(snapshot, ignore_errors=True)
            # Copy the volumes directory to the
            shutil.copytree(self.volume, snapshot, symlinks=True, ignore=lambda *args, **kwargs: ['.git'])

    def snapshot_load(self, snapshots=()):
        options = list(set(self.snapshot_ls()) & set(snapshots))
        if len(options):
            name = options[-1]
            snapshot = '%s/%s' % (self.snapshot, name)
            # Remove the current volume directory.
            shutil.rmtree(self.volume, ignore_errors=True)
            # Copy the snapshot as new volume.
            shutil.copytree(snapshot, self.volume, symlinks=True, ignore=lambda *args, **kwargs: ['.git'])
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


