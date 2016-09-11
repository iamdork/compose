import dork_compose.plugin
from docker.client import from_env


class Plugin(dork_compose.plugin.Plugin):

    def cleanup(self):
        client = from_env()
        volumes = client.volumes({'dangling': True})
        if not volumes or not volumes['Volumes']:
            return
        for volume in volumes['Volumes']:
            client.remove_volume(volume['Name'])
