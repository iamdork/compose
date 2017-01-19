import dork_compose.plugin
from docker.api.client import APIClient


class Plugin(dork_compose.plugin.Plugin):

    def cleanup(self):
        client = APIClient()
        # Remove unused volumes.
        volumes = client.volumes({'dangling': True})
        if volumes and volumes['Volumes']:
            for volume in volumes['Volumes']:
                try:
                    client.remove_volume(volume['Name'])
                except Exception:
                    pass

        # Remove unused images.
        images = client.images(filters={'dangling': True})
        if images:
            for image in images:
                try:
                    client.remove_image(image['Id'], force=True)
                except Exception:
                    pass
