import dork_compose.plugin
from docker.client import from_env


class Plugin(dork_compose.plugin.Plugin):

    def cleanup(self):
        client = from_env()
        # Remove unused volumes.
        volumes = client.volumes({'dangling': True})
        if volumes and volumes['Volumes']:
            for volume in volumes['Volumes']:
                client.remove_volume(volume['Name'])

        # Remove unused images.
        images = client.images(filters={'dangling': True})
        if images:
            for image in images:
                client.remove_image(image['Id'], force=True)
