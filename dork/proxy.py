from environment import env, project, instance
from docker import Client
import logging
log = logging.getLogger(__name__)


@env('DORK_DOMAIN')
def domain():
    return '127.0.0.1.xip.io'


@env('DORK_SUBDOMAIN')
def subdomain():
    return project() if project() == instance() else '%s--%s' % (project(), instance())


@env('DORK_PROXY_IMAGE')
def proxy_image():
    return 'jwilder/nginx-proxy'


def process_config(config):
    for service in config.services:
        if 'ports' in service:
            for index, port in enumerate(service['ports']):
                if isinstance(port, basestring):
                    (external, internal) = port.split(':')
                    if external and internal:
                        # service['ports'][index] = int(internal)
                        if 'environment' not in service:
                            service['environment'] = {}
                        service['environment']['VIRTUAL_HOST'] = '%s.%s' % (subdomain(), domain())
            service['ports'] = []
    return config


def initialize():
    client = Client()
    if not client.images(name=proxy_image()):
        client.pull(proxy_image())

    if not client.containers(filters={'name': 'dork_proxy'}, all=True):
        client.create_container(
            image=proxy_image(),
            name='dork_proxy',
            detach=True
        )

    for container in client.containers(filters={'name': 'dork_proxy'}, all=True):
        info = client.inspect_container(container)
        if not info['State']['Running']:
            client.start(
                container=container,
                binds=['/run/docker.sock:/tmp/docker.sock:ro'],
                port_bindings={'80': '80', '443': '443'}
            )
