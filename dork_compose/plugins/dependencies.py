import dork_compose.plugin
import time
from docker.client import from_env

from docker.errors import APIError

import logging
log = logging.getLogger(__name__)


class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name, command):
        if command == 'run':
            raise StandardError('Skip dependencies plugin on "run" command.')
        super(Plugin, self).__init__(env, name, command)

    def after_build(self, service, no_cache, pull, force_rm):
        client = from_env()
        image = client.inspect_image(service.image_name)
        root = None
        source = None
        if image.get('Config', {}).get('Labels'):
            root = image.get('Config', {}).get('Labels', {}).get('dork.root', None)
            source = image.get('Config', {}).get('Labels', {}).get('dork.source', None)
        if not root:
            return

        deps = filter(lambda x: x, image.get('Config', {}).get('Labels', {}).get('dork.dependencies', '').split(';'))

        hotcode = []
        if service.options and service.options.get('labels'):
            hotcode = service.options\
                .get('labels')\
                .get('dork.hotcode', image.get('Config', {})
                     .get('Labels', {}).get('dork.hotcode', ''))

            hotcode = filter(lambda x: x, hotcode.split(';'))
        hotcode.append('.git')

        if not (source and root and deps):
            return

        try:
            client.inspect_image('iamdork/rsync')
        except APIError:
            client.pull('iamdork/rsync')

        container = client.create_container(
            image=service.image_name,
            volumes=['/'.join([root, path]) for path in deps],
        )['Id']

        try:
            dork_source = self.env.get('DORK_SOURCE')
            for path in deps:
                src = '/'.join([root, path])
                dst = '/'.join([dork_source, source, path])
                log.info("Synching %s to %s." % (src, dst))
                sync = client.create_container(
                    image='iamdork/rsync',
                    volumes=['/destination'],
                    host_config=client.create_host_config(
                        binds=['%s:/destination' % dst],
                        volumes_from=container
                    ),
                    environment={
                        'SOURCE': src,
                        'EXCLUDE': ' '.join(hotcode)
                    }
                )['Id']
                try:
                    client.start(sync)
                    while client.inspect_container(sync)['State']['Running']:
                        time.sleep(0.5)
                finally:
                   client.remove_container(sync)
        finally:
            client.remove_container(container)
