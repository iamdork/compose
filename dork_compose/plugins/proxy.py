import dork_compose.plugin
from dork_compose.helpers import notdefault, tru
from compose.cli.command import get_client
from compose.config import config
from compose.project import Project
import os
import glob
import pkg_resources
from compose.const import API_VERSIONS, COMPOSEFILE_V2_0
import urlparse


class Plugin(dork_compose.plugin.Plugin):

    def initialize(self):
        self.auth = self.collect_auth_files()
        return True

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
        return os.path.expanduser(self.env.get('DORK_PROXY_AUTH_DIR', '%s/auth' % self.datadir))

    @property
    def docker_sock(self):
        result = urlparse.urlparse(self.env.get('DOCKER_HOST', 'unix:///var/run/docker.sock'))
        if result.scheme != 'unix':
            raise EnvironmentError('Dork proxy works with docker socket api only.')
        return result.path

    @property
    def proxy_domain(self):
        return self.env.get('DORK_PROXY_DOMAIN', '127.0.0.1.xip.io')

    def reload_proxy(self):
        client = get_client(
            verbose=False,
            version=API_VERSIONS[COMPOSEFILE_V2_0],
            tls_config=None,
            host=None,
            environment=self.env
        )
        containers = client.containers(all=True, filters={
            'label': 'org.iamdork.proxy'
        })

        for container in containers:
            ex = client.exec_create(container, 'nginx -s reload')
            client.exec_start(ex)

    def preprocess_config(self, config):
        for service in config.services:
            if 'environment' in service and 'DORK_PROXY_SKIP' in service['environment']:
                continue
            if 'ports' in service:
                for index, port in enumerate(service['ports']):
                    if isinstance(port, basestring):
                        (external, internal) = port.split(':')
                        if external and internal:
                            domain = self.service_domain() if external == '80' or external == '443' else self.service_domain(service['name'])
                            if 'environment' not in service:
                                service['environment'] = {}
                            service['environment']['VIRTUAL_HOST'] = domain
                            if 'labels' not in service:
                                service['labels'] = {}
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

    def get_project(self, networks):
        environment = {}
        environment.update(self.env)
        environment.update({
            'DOCKER_SOCK': self.docker_sock,
            'DORK_PROXY_AUTH_DIR': self.auth_dir
        })

        config_details = config.find(
            base_dir=pkg_resources.resource_filename('dork_compose', 'proxy'),
            filenames=None,
            environment=environment
        )

        config_data = config.load(config_details)
        for network in networks:
            config_data.networks[network] = {
                'external': {'name': network},
                'external_name': network
            }

            for key, service in enumerate(config_data.services):
                if config_data.services[key]['name'] == 'front':
                    if 'networks' not in config_data.services[key]:
                        config_data.services[key]['networks'] = {}
                    config_data.services[key]['networks'][network] = None

        api_version = environment.get(
            'COMPOSE_API_VERSION',
            API_VERSIONS[config_data.version])

        client = get_client(
            verbose=False,
            version=api_version,
            tls_config=None,
            host=None,
            environment=environment
        )
        return Project.from_config('dork_proxy', config_data, client)

    def get_networks(self):
        result = []
        client = get_client(
            verbose=False,
            version=API_VERSIONS[COMPOSEFILE_V2_0],
            tls_config=None,
            host=None,
            environment=self.env
        )
        containers = client.containers(all=True, filters={
            'label': 'org.iamdork.proxy'
        })
        for container in containers:
            if 'NetworkSettings' in container and 'Networks' in container['NetworkSettings']:
                for network in container['NetworkSettings']['Networks']:
                    result.append(network)
        return result

    def initialized_networks(self, networks):
        if 'default' in networks and networks['default'].project != 'dork_proxy':
            current_networks = self.get_networks()
            if networks['default'].full_name not in current_networks:
                current_networks.append(networks['default'].full_name)
            project = self.get_project(current_networks)
            project.up(detached=True, remove_orphans=True)

    def removing_networks(self, networks):
        if 'default' in networks and networks['default'].project != 'dork_proxy':
            current_networks = list(set(self.get_networks()) - {networks['default'].full_name})
            project = self.get_project(current_networks)

            if current_networks:
                project.up(detached=True, remove_orphans=True)
            else:
                project.down(remove_image_type=None, include_volumes=False, remove_orphans=True)
