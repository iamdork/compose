import dork.plugin
from docker import Client
from dork.helpers import notdefault, tru
import os
import glob


class Plugin(dork.plugin.Plugin):

    def initialize(self):
        self.hosts = {}
        try:
            self.__client = Client()

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
                binds = ['/run/docker.sock:/tmp/docker.sock:ro']
                if self.auth_dir:
                    binds.append('%s:/etc/nginx/htpasswd' % self.auth_dir)
                self.__client.start(
                    container=container,
                    binds=binds,
                    port_bindings={'80': '80', '443': '443'},
                )
            self.proxy_service = container
            return True

        except Exception as exc:
            return False

    def service_domain(self, service=None):
        return '--'.join(filter(tru, [
            service,
            notdefault(self.project),
            notdefault(self.instance)
        ])) + '.' + self.proxy_domain

    @property
    def auth_dir(self):
        name = 'DORK_PROXY_AUTH_DIR'
        return os.path.expanduser(self.env[name]) if name in self.env else None

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

    def initialized_networks(self, networks):

        if self.auth_dir:
            auth = self.collect_auth_files()
            for name, host in self.hosts.iteritems():
                file = []
                if '.auth' in auth:
                    file.extend(auth['.auth'])
                if '.auth.%s' % name in auth:
                    file.extend(auth['.auth.%s' % name])
                if file :
                    with open('%s/%s' % (self.auth_dir, host), mode='w+') as f:
                        f.writelines(file)

        if 'default' in networks:
            network = networks['default'].full_name
            if network not in self.proxy_service['NetworkSettings']['Networks']:
                self.__client.connect_container_to_network(self.proxy_service, network)
                self.reload_proxy()

    def removing_networks(self, networks):

        if self.auth_dir:
            for name, host in self.hosts.iteritems():
                f = '%s/%s' % (self.auth_dir, host)
                if os.path.exists(f):
                    os.remove(f)

        if 'default' in networks:
            network = networks['default'].full_name
            if network in self.proxy_service['NetworkSettings']['Networks']:
                self.__client.disconnect_container_from_network(self.proxy_service, network)
                self.reload_proxy()
