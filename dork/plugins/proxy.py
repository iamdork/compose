import dork.plugin
import logging
from docker import Client
from dork.helpers import notdefault, tru
import os
import glob
log = logging.getLogger(__name__)

proxy_image = 'jwilder/nginx-proxy'


def proxy_container(client):
    if not client.images(name=proxy_image):
        log.info('pulling %s image.' % proxy_image)
        client.pull(proxy_image)

    if not client.containers(filters={'name': 'dork_proxy'}, all=True):
        log.info('creating proxy container.')
        client.create_container(
            image=proxy_image,
            name='dork_proxy',
            detach=True
        )

    container = client.containers(filters={'name': 'dork_proxy'}, all=True)[0]
    if not container['State'] == 'running':
        log.info('starting proxy container.')
        binds = ['/run/docker.sock:/tmp/docker.sock:ro']
        if 'DORK_PROXY_AUTH_DIR' in os.environ:
            binds.append('%s:/etc/nginx/htpasswd' % os.path.expanduser(os.environ['DORK_PROXY_AUTH_DIR']))
        client.start(
            container=container,
            binds=binds,
            port_bindings={'80': '80', '443': '443'},
        )
    return container


class Plugin(dork.plugin.Plugin):

    def initialize(self):
        self.__client = Client()

    def domain(self, service=None):
        return '--'.join(filter(tru, [
            service,
            notdefault(self.project),
            notdefault(self.instance)
        ])) + '.' + self.base_domain

    @property
    def base_domain(self):
        return self.env.get('DORK_PROXY_DOMAIN', '127.0.0.1.xip.io')

    def preprocess_config(self, config):
        for service in config.services:
            if 'ports' in service:
                for index, port in enumerate(service['ports']):
                    if isinstance(port, basestring):
                        (external, internal) = port.split(':')
                        if external and internal:
                            if 'environment' not in service:
                                service['environment'] = {}
                            domain = self.domain() if external == '80' or external == '443' else self.domain(service['name'])
                            service['environment']['VIRTUAL_HOST'] = domain
                            if external == '443':
                                service['environment']['VIRTUAL_PROTO'] = 'https'
                            service['environment']['VIRTUAL_PORT'] = int(internal)
                service['ports'] = []


        if 'DORK_PROXY_AUTH_DIR' not in os.environ:
            return
        auth = self.collect_auth_files()
        for service in config.services:
            file = []
            if '.auth' in auth:
                file.extend(auth['.auth'])
            if '.auth.%s' % service['name'] in auth:
                file.extend(auth['.auth.%s' % service['name']])
            if file and 'environment' in service and 'VIRTUAL_HOST' in service['environment']:
                with open('%s/%s' % (os.path.expanduser(os.environ['DORK_PROXY_AUTH_DIR']), service['environment']['VIRTUAL_HOST']), mode='w+') as f:
                    f.writelines(file)

    def collect_auth_files(self):
        files = {}
        path = filter(len, self.basedir.split('/'))
        current = ''
        while len(path):
            current = current + '/' + path.pop(0)
            auth = '%s/.auth' % current
            if os.path.isfile(auth):
                if '.auth' not in files:
                    files['.auth'] = []
                with open(auth) as f:
                    files['.auth'].append(f.read())
            for file in glob.glob('%s/.auth.*' % current):
                filename = os.path.basename(file)
                if filename not in files:
                    files[filename] = []
                with open(file) as f:
                    files[filename].append(f.read())

        return files

    def initialize_networks(self, networks, services):
        if 'default' in networks:
            network = networks['default'].full_name
            container = proxy_container(self.__client)
            if network not in container['NetworkSettings']['Networks']:
                self.__client.connect_container_to_network(container, network)


    def remove_networks(self, networks, services):
        if 'default' in networks:
            network = networks['default'].full_name
            container = proxy_container(self.__client)
            if network in container['NetworkSettings']['Networks']:
                self.__client.disconnect_container_from_network(container, network)
