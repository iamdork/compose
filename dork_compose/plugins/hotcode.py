import dork_compose.plugin
from compose.config.config import VolumeSpec
import re

class Plugin(dork_compose.plugin.Plugin):
    @property
    def paths(self):
        return filter(lambda x: x, self.env.get('DORK_HOT_CODE_PATHS', '').split(';'))

    def preprocess_config(self, config):
        """
        Inject dummy volumes in config, so the container gets recreated when hot
        code paths change.
        """
        for service in config.services:
            src = self.env['DORK_SOURCE']
            for path in self.paths:
                if 'volumes' not in service:
                    service['volumes'] = []

                service['volumes'].append(VolumeSpec.parse('%s/%s:/dork.hotcode.root/%s' % (
                    src, path, path
                )))

    def creating_container(self, service):
        """
        If image has dork.hotcode.root label, replace dummy volumes with real ones
        or remove them at all.
        """
        volumes = []
        image = service.client.inspect_image(service.image_name)
        root = image.get('Config', {}).get('Labels', {}).get('dork.hotcode.root')
        for volume in service.options['volumes']:
            if re.search('^/dork\.hotcode\.root', volume.internal):
                if root:
                    volumes.append(VolumeSpec.parse(':'.join([
                        volume.external,
                        volume.internal.replace('/dork.hotcode.root', root.rstrip('/')),
                        volume.mode
                    ])))
            else:
                volumes.append(volume)
        service.options['volumes'] = volumes


