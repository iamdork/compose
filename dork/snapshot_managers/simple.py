from dork.environment import env
from dork.environment import project, instance
import os
import shutil
from compose.config.config import VolumeSpec, Config


@env('DORK_SIMPLE_VOLUME_PATH')
def simple_volume_path():
    return '/var/dork/volumes'


@env('DORK_SIMPLE_SNAPSHOT_PATH')
def simple_snapshot_path():
    return '/var/dork/snapshots'


@env('DORK_SIMPLE_SNAPSHOT_DIR')
def simple_snapshot_dir():
    return '%s/%s' % (os.path.expanduser(simple_snapshot_path()), project())


@env('DORK_SIMPLE_VOLUME_DIR')
def simple_volume_dir():
    return '%s/%s/%s' % (os.path.expanduser(simple_volume_path()), project(), instance())


def __mkdir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def initialize():
    # Ensure snapshot and volume directories exist.
    __mkdir(simple_snapshot_dir())
    __mkdir(simple_volume_dir())


def remove():
    shutil.rmtree(simple_volume_dir())


def save(name):
    snapshot = '%s/%s' % (simple_snapshot_dir(), name)
    volume = simple_volume_dir()
    # Remove the current snapshot, if one exists.
    shutil.rmtree(snapshot, ignore_errors=True)
    # Copy the volumes directory to the
    shutil.copytree(volume, snapshot)


def rm(name):
    snapshot = '%s/%s' % (simple_snapshot_dir(), name)
    # Remove the current snapshot, if one exists.
    shutil.rmtree(snapshot, ignore_errors=True)


def load(name):
    snapshot = '%s/%s' % (simple_snapshot_dir(), name)
    volume = simple_volume_dir()
    # Remove the current volume directory.
    shutil.rmtree(volume, ignore_errors=True)
    # Copy the snapshot as new volume.
    shutil.copytree(snapshot, volume)


def reset():
    volume = simple_volume_dir()
    # Remove the current volume directory.
    shutil.rmtree(volume, ignore_errors=True)
    # Re-create the volume directory.
    __mkdir(volume)


def ls():
    return [path for path in os.listdir(simple_snapshot_dir())]


def process_config(config):
    for service in config.services:
        if 'volumes' in service:
            for index, volume in enumerate(service['volumes']):
                if volume.is_named_volume:
                    service['volumes'][index] = VolumeSpec.parse('%s/%s:%s' % (
                        simple_volume_dir(),
                        volume.external,
                        volume.internal
                    ))
    return config
    # Create a new config without volumes.
    return Config(config.version, config.services, {}, config.networks)
