import dork_compose.plugin
from compose.config.config import VolumeSpec
from docker.client import from_env
from docker.errors import APIError, NotFound


class Plugin(dork_compose.plugin.Plugin):

    def get_hotcode_volumes(self, image):
        root = None
        source = '.'
        if image.get('Config', {}).get('Labels'):
            root = image.get('Config', {}).get('Labels', {}).get('dork.root')
            source = image.get('Config', {}).get('Labels', {}).get('dork.source', '.')
        if not root:
            return []

        paths = filter(lambda x: x, image.get('Config', {}) \
            .get('Labels', {}) \
            .get('dork.hotcode', '') \
            .split(';'))

        return [VolumeSpec.parse(':'.join([
            '%s/%s/%s' % (self.env['DORK_SOURCE'], source, path),
            '%s/%s' % (root.rstrip('/'), path),
            'rw'
        ])) for path in paths]

    def creating_container(self, service):
        """
        Inject volumes for all hot code paths.
        """
        try:
            image = service.client.inspect_image(service.image_name)
        except APIError:
            return
        externals = [v.external for v in service.options['volumes']]
        for v in self.get_hotcode_volumes(image):
            if v.external not in externals:
                service.options['volumes'].append(v)






