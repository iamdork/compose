import dork_compose.plugin
from docker import Client
from dork_compose.helpers import notdefault, tru
from compose.service import Service
import os
import glob


class Plugin(dork_compose.plugin.Plugin):

    def initialize(self):
        self.hosts = {}
        self.auth = self.collect_auth_files()
        self.__client = Client()
        return True

    @property
    def proxy_service(self):
        service = Service(
            name='proxy',
            client=self.__client,
            project='dork_services',
            use_networking=True,
            options={
                'image': self.proxy_image
            }
        )
        service.start()

        if not self.__client.images(name=self.proxy_image):
            self.log.info('pulling %s image.' % self.proxy_image)
            self.__client.pull(self.proxy_image)

        if not self.__client.containers(filters={'name': 'dork_proxy'}, all=True):
            self.log.info('creating proxy container.')
            self.__client.create_container(
                image=self.proxy_image,
                name='dork_proxy',
                detach=True
            )

        container = self.__client.containers(filters={'name': 'dork_proxy'}, all=True)[0]

        if not container['State'] == 'running':
            self.log.info('starting proxy container.')
            self.__client.start(
                container=container,
                binds=[
                    '%s:/tmp/docker.sock:ro' % self.docker_sock,
                    '%s:/etc/nginx/htpasswd' % self.auth_dir
                ],
                port_bindings={'80': '80', '443': '443'},
            )
        return container

    def service_domain(self, service=None):
        return '--'.join(filter(tru, [
            service,
            notdefault(self.project),
            notdefault(self.instance)
        ])) + '.' + self.proxy_domain

    def info(self, project):
        info = {}
        auth = self.collect_auth_files()
        for service in project.services:
            if 'environment' in service.options and 'VIRTUAL_HOST' in service.options['environment']:
                key = '"%s" url' % service.name
                info[key] = service.options['environment'].get('VIRTUAL_PROTO', 'http') + '://' + service.options['environment']['VIRTUAL_HOST']
                if '.auth' in auth or '.auth.%s' % service.name in auth:
                    info[key] += ' (password protected)'
        return info

    @property
    def auth_dir(self):
        return os.path.expanduser(self.env.get('DORK_PROXY_AUTH_DIR', '~/.dork/auth'))

    @property
    def docker_sock(self):
        return self.env.get('DOCKER_SOCK', '/run/docker.sock')

    @property
    def proxy_domain(self):
        return self.env.get('DORK_PROXY_DOMAIN', '127.0.0.1.xip.io')

    @property
    def proxy_image(self):
        return self.env.get('DORK_PROXY_IMAGE', 'jwilder/nginx-proxy')

    def reload_proxy(self):
        ex = self.__client.exec_create(self.proxy_service, 'nginx -s reload')
        self.__client.exec_start(ex)

    def preprocess_config(self, config):
        for service in config.services:
            if 'ports' in service:
                for index, port in enumerate(service['ports']):
                    if isinstance(port, basestring):
                        (external, internal) = port.split(':')
                        if external and internal:
                            if 'environment' not in service:
                                service['environment'] = {}
                            domain = self.service_domain() if external == '80' or external == '443' else self.service_domain(service['name'])
                            self.hosts[service['name']] = domain
                            service['environment']['VIRTUAL_HOST'] = domain
                            if external == '443':
                                service['environment']['VIRTUAL_PROTO'] = 'https'
                            service['environment']['VIRTUAL_PORT'] = int(internal)
                service['ports'] = []

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

    def starting_service(self, service):
        if self.auth_dir and 'environment' in service.options and 'VIRTUAL_HOST' in service.options['environment']:
            lines = []
            if '.auth' in self.auth:
                lines.extend(self.auth['.auth'])
            if '.auth.%s' % service.name in self.auth:
                lines.extend(self.auth['.auth.%s' % service.name])
            authfile = '%s/%s' % (self.auth_dir, service.options['environment']['VIRTUAL_HOST'])
            if lines:
                with open(authfile, mode='w+') as f:
                    f.writelines(lines)
            elif os.path.exists(authfile):
                os.remove(authfile)
            self.reload_proxy()

    def initialized_networks(self, networks):

        if 'default' in networks:
            network = networks['default'].full_name
            if network not in self.proxy_service['NetworkSettings']['Networks']:
                self.__client.connect_container_to_network(self.proxy_service, network)

    def removing_networks(self, networks):

        if 'default' in networks:
            network = networks['default'].full_name
            if network in self.proxy_service['NetworkSettings']['Networks']:
                self.__client.disconnect_container_from_network(self.proxy_service, network)
