import dork_compose.plugin
from compose.cli.docker_client import docker_client
from dork_compose.helpers import notdefault, tru
import os
import glob
import urlparse
import pkg_resources


class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name):
        dork_compose.plugin.Plugin.__init__(self, env, name)
        self.auth = self.collect_auth_files()

    def environment(self):
        return {
            'DOCKER_SOCK': self.docker_sock,
            'DORK_PROXY_AUTH_DIR': self.auth_dir
        }

    @property
    def auxiliary_project(self):
        return pkg_resources.resource_filename('dork_compose', 'auxiliary/proxy')

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
        client = docker_client(self.env)
        containers = client.containers(all=True, filters={
            'label': 'org.iamdork.proxy'
        })

        for container in containers:
            ex = client.exec_create(container, 'nginx -s reload')
            client.exec_start(ex)

    def preprocess_config(self, config):
        for service in config.services:
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

    def initializing(self, project, service_names=None):
        for service in project.get_services():
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
