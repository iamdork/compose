import dork_compose.plugin
import time
from compose.config.config import VolumeSpec

from docker.errors import APIError


class Plugin(dork_compose.plugin.Plugin):

    def creating_container(self, service):
        try:
            image = service.client.inspect_image(service.image_name)
        except APIError:
            return

        root = None
        if image.get('Config', {}).get('Labels'):
            root = image.get('Config', {}).get('Labels', {}).get('dork.root', None)
        if not root:
            return

        deps = filter(lambda x: x, image.get('Config', {}).get('Labels', {}).get('dork.dependencies', '').split(';'))
        for dep in deps:
            service.options['volumes'].append(VolumeSpec.parse('%s/%s' % (root, dep)))

    def initialized(self, project, containers=None):
        source = self.env.get('DORK_SOURCE')
        for container in containers:
            root = container.labels.get('dork.root', None)
            dsource = container.labels.get('dork.source', '.')
            deps = filter(lambda x: x, container.labels.get('dork.dependencies', '').split(';'))
            if root:
                for path in deps:
                    src = '/'.join([root, path])
                    dst = '/'.join([source, dsource, path])
                    print "Synching %s to %s." % (src, dst)

                    try:
                        image = container.client.inspect_image('iamdork/rsync')
                    except APIError:
                        container.client.pull('iamdork/rsync')

                    sync = container.client.create_container(
                        image='iamdork/rsync',
                        volumes=['/destination'],
                        host_config=container.client.create_host_config(binds=[
                            '%s:/destination' % dst
                        ]),
                        environment={
                            'SOURCE': src,
                            'EXCLUDE': '.git'
                        }
                    )

                    try:
                        container.client.start(sync, volumes_from=container.id)
                        while container.client.inspect_container(sync)['State']['Running']:
                            time.sleep(0.5)
                    finally:
                        container.client.remove_container(sync)


