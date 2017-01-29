import dork_compose.plugin
from compose.cli.docker_client import docker_client
from dork_compose.helpers import notdefault, tru
import os
import urlparse
import pkg_resources
from subprocess import check_call

import logging
log = logging.getLogger(__name__)


class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name, command):
        dork_compose.plugin.Plugin.__init__(self, env, name, command)

    def environment(self):
        return {
            'DORK_PROXY_HTTPS_METHOD': self.https_method,
            'DORK_PROXY_HTTPS_SIGNING': self.https_signing,
            'DOCKER_SOCK': self.docker_sock,
            'DORK_PROXY_AUTH_DIR': self.auth_dir,
            'DORK_PROXY_CERTS_DIR': self.certs_dir,
            'DORK_PROXY_DOMAIN': self.proxy_domain,
            'DORK_PROXY_INSTANCE_DOMAIN': self.service_domain(),
            'DORK_PROXY_LETSENCRYPT_EMAIL': self.letsencrypt_email,
        }

    @property
    def https_signing(self):
        return self.env.get('DORK_PROXY_HTTPS_SIGNING', 'selfsigned')

    @property
    def auxiliary_project(self):
        return pkg_resources.resource_filename('dork_compose', 'auxiliary/proxy/%s' % self.https_signing)

    def service_domain(self, service=None):
        return '--'.join(filter(tru, [
            service,
            notdefault(self.project),
            notdefault(self.instance)
        ])) + '.' + self.proxy_domain

    def info(self, project):
        info = {}

        auth = self.collect_auth_files([service.name for service in project.services])
        for service in project.services:
            if 'environment' in service.options and 'VIRTUAL_HOST' in service.options['environment']:
                key = '%s url' % service.name
                info[key] = service.options['environment'].get('VIRTUAL_PROTO', 'http') + '://' + service.options['environment']['VIRTUAL_HOST']
                if service.name in auth and auth[service.name]:
                    info[key] += ' (password protected)'
        return info

    @property
    def https_method(self):
        return os.path.expanduser(self.env.get('DORK_PROXY_HTTPS_METHOD', 'noredirect'))

    @property
    def auth_dir(self):
        return os.path.expanduser(self.env.get('DORK_PROXY_AUTH_DIR', '%s/auth' % self.datadir))

    @property
    def certs_dir(self):
        return os.path.expanduser(self.env.get('DORK_PROXY_CERTS_DIR', '%s/certs' % self.datadir))

    @property
    def docker_sock(self):
        result = urlparse.urlparse(self.env.get('DOCKER_HOST', 'unix:///var/run/docker.sock'))
        if result.scheme != 'unix':
            raise EnvironmentError('Dork proxy works with docker socket api only.')
        return result.path

    @property
    def proxy_domain(self):
        return self.env.get('DORK_PROXY_DOMAIN', 'dork.io')

    @property
    def letsencrypt_email(self):
        return self.env.get('DORK_PROXY_LETSENCRYPT_EMAIL', 'admin@localhost')

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
                indices = range(len(service['ports']))
                indices.reverse()
                for index in indices:
                    port = service['ports'][index]
                    if isinstance(port, basestring):
                        if ':' not in port:
                            continue
                        (external, internal) = port.split(':')
                        if external and internal:
                            domain = self.service_domain() if external == '80' or external == '443' else self.service_domain(service['name'])
                            if 'environment' not in service:
                                service['environment'] = {}
                            service['environment']['VIRTUAL_HOST'] = domain
                            service['environment']['LETSENCRYPT_HOST'] = domain
                            service['environment']['LETSENCRYPT_EMAIL'] = self.letsencrypt_email
                            if 'labels' not in service:
                                service['labels'] = {}
                            service['environment']['VIRTUAL_PORT'] = int(internal)
                            service['ports'][index] = internal

    def collect_auth_files(self, services):
        files = {service: [] for service in services}

        path = filter(len, self.basedir.split('/'))
        current = ''
        while len(path):
            current = current + '/' + path.pop(0)

            auth = '%s/.auth' % current
            if os.path.isfile(auth):
                with open(auth) as f:
                    for service in services:
                        files[service].append(f.read())

            no_auth = '%s/.no_auth' % current
            if os.path.isfile(no_auth):
                for service in services:
                    if service in files:
                        files[service] = []

            for service in services:
                auth = '%s/.auth.%s' % (current, service)
                no_auth = '%s/.no_auth.%s' % (current, service)
                if os.path.isfile(auth):
                    with open(auth) as f:
                        files[service].append(f.read())
                if os.path.isfile(no_auth):
                    files[service] = []

        return files

    def initializing(self, project, service_names=None):
        if self.https_signing == 'selfsigned':
            if not os.path.isdir(self.certs_dir):
                os.makedirs(self.certs_dir)

            if not os.path.isfile(self.certs_dir + '/dhparam.pem'):
                log.info("Creating Diffie-Hellman group. This might take a while.")
                check_call(['openssl', 'dhparam', '-out', '%s/dhparam.pem' % self.certs_dir, '2048'])

            key = '%s/%s.key' % (self.certs_dir, self.proxy_domain)
            crt = '%s/%s.crt' % (self.certs_dir, self.proxy_domain)

            if not os.path.isfile(key) or not os.path.isfile(crt):
                log.info("Creating self signed key and certificate for domain '%s'." % self.proxy_domain)
                check_call([
                    'openssl', 'req', '-x509', '-nodes',
                    '-days', '365', '-newkey', 'rsa:2048',
                    '-keyout', key,
                    '-out', crt,
                    # TODO: fix signed parameters
                    '-subj', '/C=GB/ST=London/L=London/O=Global Security/OU=IT Department/CN=*.%s' % self.proxy_domain
                ])

        auth = self.collect_auth_files([service.name for service in project.get_services()])

        for service in project.get_services():
            if self.auth_dir and 'environment' in service.options and 'VIRTUAL_HOST' in service.options['environment']:
                lines = auth[service.name]
                authfile = '%s/%s' % (self.auth_dir, service.options['environment']['VIRTUAL_HOST'])
                if lines:
                    if not os.path.isdir(self.auth_dir):
                        os.makedirs(self.auth_dir)
                    with open(authfile, mode='w+') as f:
                        f.writelines(lines)
                elif os.path.exists(authfile):
                    os.remove(authfile)

    def removed(self, project, include_volumes=False):
        for service in project.get_services():
            if self.auth_dir and 'environment' in service.options and 'VIRTUAL_HOST' in service.options['environment']:
                authfile = '%s/%s' % (self.auth_dir, service.options['environment']['VIRTUAL_HOST'])
                if os.path.isfile(authfile):
                    os.remove(authfile)


