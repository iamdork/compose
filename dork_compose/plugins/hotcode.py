import dork_compose.plugin
from compose.config.config import VolumeSpec
from docker.client import from_env
from docker.errors import APIError, NotFound


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
            # root = service.options.get('labels').get('dork.root', root)
            # source = service.options.get('labels').get('dork.source', source)
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
        externals = [v.external for v in service.options['volumes']]
        for v in self.get_hotcode_volumes(service):
            if v.external not in externals:
                service.options['volumes'].append(v)






