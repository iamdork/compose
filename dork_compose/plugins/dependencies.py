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
        root = None
        source = '.'
        hotcode = ''
        dependencies = ''
        try:
            image = service.client.inspect_image(service.image_name)
            if image.get('Config', {}).get('Labels'):
                root = image.get('Config', {}).get('Labels', {}).get('dork.root')
                source = image.get('Config', {}).get('Labels', {}).get('dork.source', '.')
                hotcode = image.get('Config', {}).get('Labels', {}).get('dork.hotcode', '')
                dependencies = image.get('Config', {}).get('Labels', {}).get('dork.dependencies', '')
        except APIError:
            pass

        if isinstance(service.options.get('labels'), dict):
            root = service.options.get('labels', {}).get('dork.root', root)
            source = service.options.get('labels', {}).get('dork.source', source)
            hotcode = service.options.get('labels').get('dork.hotcode', hotcode)
            dependencies = service.options.get('labels').get('dork.dependencies', dependencies)

        deps = filter(lambda x: x, dependencies.split(';')) if dependencies else []
        hot = filter(lambda x: x, hotcode.split(';')) if hotcode else []
        hot.append('.git')

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
                        'EXCLUDE': ' '.join(hot)
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
