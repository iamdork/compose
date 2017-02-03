import dork_compose.plugin
from compose.config.config import VolumeSpec
from docker.api.client import APIClient
import logging
log = logging.getLogger(__name__)
import time

from docker.errors import APIError


class Plugin(dork_compose.plugin.Plugin):

    def get_hotcode_volumes(self, service):
        root = None
        source = '.'
        hotcode = ''
        try:
            image = service.client.inspect_image(service.image_name)
            if image.get('Config', {}).get('Labels'):
                root = image.get('Config', {}).get('Labels', {}).get('dork.root')
                source = image.get('Config', {}).get('Labels', {}).get('dork.source', '.')
                hotcode = image.get('Config', {}).get('Labels', {}).get('dork.hotcode', '')
        except APIError:
            pass

        if isinstance(service.options.get('labels'), dict):
            root = service.options.get('labels', {}).get('dork.root', root)
            source = service.options.get('labels', {}).get('dork.source', source)
            hotcode = service.options.get('labels').get('dork.hotcode', hotcode)

        if not root:
            return []

        paths = filter(lambda x: x, hotcode.split(';'))

        return [VolumeSpec.parse(':'.join([
            '%s/%s/%s' % (self.env['DORK_SOURCE'], source, path),
            '%s/%s' % (root.rstrip('/'), path),
            'rw'
        ])) for path in paths]

    def creating_container(self, service):
        """
        Inject volumes for all hot code paths.
        """
        self.sync_code(service=service)
        externals = [v.external for v in service.options['volumes']]
        for v in self.get_hotcode_volumes(service):
            if v.external not in externals:
                service.options['volumes'].append(v)

    def sync_code(self, service):
        client = APIClient()
        root = None
        source = '.'
        hotcode = ''
        try:
            image = service.client.inspect_image(service.image_name)
            if image.get('Config', {}).get('Labels'):
                root = image.get('Config', {}).get('Labels', {}).get('dork.root')
                source = image.get('Config', {}).get('Labels', {}).get('dork.source', '.')
                hotcode = image.get('Config', {}).get('Labels', {}).get('dork.hotcode', '')
        except APIError:
            pass

        if isinstance(service.options.get('labels'), dict):
            root = service.options.get('labels', {}).get('dork.root', root)
            source = service.options.get('labels', {}).get('dork.source', source)
            hotcode = service.options.get('labels').get('dork.hotcode', hotcode)

        hot = filter(lambda x: x, hotcode.split(';')) if hotcode else []
        hot.append('.git')
        hot.append('.env')
        hot.append('.dork.env')

        if not (source and root):
            return

        try:
            client.inspect_image('iamdork/rsync')
        except APIError:
            client.pull('iamdork/rsync')

        container = client.create_container(
            image=service.image_name,
            volumes=[root],
        )['Id']

        try:
            dork_source = self.env.get('DORK_SOURCE')
            src = root
            dst = '/'.join([dork_source, source])
            log.info("Synching %s to %s." % (src, dst))
            sync = client.create_container(
                image='iamdork/rsync',
                volumes=['/destination'],
                cpu_shares=256,
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





