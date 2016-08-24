import dork_compose.plugin
from compose.config.config import VolumeSpec


class Plugin(dork_compose.plugin.Plugin):
    @property
    def paths(self):
        return filter(lambda x: x, self.env.get('DORK_HOT_CODE_PATHS', '').split(';'))

    def creating_container(self, service):
        """
        Inject volumes for all hot code paths.
        """
        service.ensure_image_exists()
        image = service.client.inspect_image(service.image_name)
        root = image.get('Config', {}).get('Labels', {}).get('dork.hotcode.root')
        if not root:
            return

        src = self.env['DORK_SOURCE']
        for path in self.paths:
            service.options['volumes'].append(VolumeSpec.parse(':'.join([
                '%s/%s' % (src, path),
                '%s/%s' % (root.rstrip('/'), path),
                'rw'
            ])))


