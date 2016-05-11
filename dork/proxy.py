from environment import env, project, instance
from docker import Client
from compose.network import ProjectNetworks
import logging

log = logging.getLogger(__name__)

proxy_image = 'jwilder/nginx-proxy'


@env('DORK_DOMAIN')
def domain():
    return '127.0.0.1.xip.io'


@env('DORK_SUBDOMAIN')
def subdomain():
    return project() if project() == instance() else '%s--%s' % (project(), instance())


@env('DORK_DEFAULT_SERVICE')
def default_service():
    return 'http'


def proxy_container(client):
    if not client.images(name=proxy_image):
        log.info('Pulling %s image.' % proxy_image)
        client.pull(proxy_image)

    if not client.containers(filters={'name': 'dork_proxy'}, all=True):
        log.info('Creating proxy container.')
        client.create_container(
            image=proxy_image,
            name='dork_proxy',
            detach=True
        )

    container = client.containers(filters={'name': 'dork_proxy'}, all=True)[0]
    if not container['State'] == 'running':
        log.info('Starting proxy container.')
        client.start(
            container=container,
            binds=['/run/docker.sock:/tmp/docker.sock:ro'],
            port_bindings={'80': '80', '443': '443'},
        )
    return container


class DorkNetworks(ProjectNetworks):
    def initialize(self):
        client = Client()
        super(DorkNetworks, self).initialize()
        if 'default' in self.networks:
            network = self.networks['default'].full_name
            container = proxy_container(client)
            if network not in container['NetworkSettings']['Networks']:
                client.connect_container_to_network(container, network)

    def remove(self):
        client = Client()
        if 'default' in self.networks:
            network = self.networks['default'].full_name
            container = proxy_container(client)
            if network in container['NetworkSettings']['Networks']:
                client.disconnect_container_from_network(container, network)
        super(DorkNetworks, self).remove()


def process_config(config):
    for service in config.services:
        if 'ports' in service:
            for index, port in enumerate(service['ports']):
                if isinstance(port, basestring):
                    (external, internal) = port.split(':')
                    if external and internal:
                        if 'environment' not in service:
                            service['environment'] = {}
                        if service['name'] == default_service():
                            service['environment']['VIRTUAL_HOST'] = '%s.%s' % (subdomain(), domain())
                        else:
                            service['environment']['VIRTUAL_HOST'] = '%s--%s.%s' % (service['name'], subdomain(), domain())
                        service['environment']['VIRTUAL_PORT'] = int(internal)
            service['ports'] = []
    return config
