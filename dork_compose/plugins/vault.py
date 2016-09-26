import dork_compose.plugin
import pkg_resources
import hvac
import os


class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name, command):
        dork_compose.plugin.Plugin.__init__(self, env, name, command)
        self.tokens = []

    def environment(self):
        return {
            'VAULT_VERSION': self.vault_version,
            'VAULT_ROOT_TOKEN': self.vault_root_token,
            'VAULT_HOST': self.vault_host,
            'VAULT_BUILD_HOST': self.vault_build_host,
            'VAULT_PORT': self.vault_port,
            'VAULT_MODE': self.vault_mode,
        }

    @property
    def vault_mode(self):
        return self.env.get('VAULT_MODE', 'secure')

    @property
    def vault_version(self):
        return self.env.get('VAULT_VERSION', '0.6.1')

    @property
    def vault_root_token(self):
        return self.env.get('VAULT_ROOT_TOKEN', 'dork')

    @property
    def vault_host(self):
        return self.env.get('VAULT_HOST', '127.0.0.1')

    @property
    def vault_port(self):
        return self.env.get('VAULT_PORT', '8200')

    @property
    def vault_build_host(self):
        return self.env.get('VAULT_BUILD_HOST', '172.17.0.1')

    @property
    def vault_secrets(self):
        return self.env.get('VAULT_SECRETS', '').split(';')

    @property
    def auxiliary_project(self):
        return pkg_resources.resource_filename('dork_compose', 'auxiliary/vault')

    def building(self, service,  no_cache, pull, force_rm):
        if 'args' in service.options['build'] and 'VAULT_TOKEN' in service.options['build']['args']:
            client = hvac.Client(
                url="http://%s:%s" % (self.vault_host, self.vault_port),
                token=self.vault_root_token
            )

            if self.vault_mode == 'secure':
                token = client.create_token()['auth']['client_token']
                self.tokens.append(token)
            else:
                token = self.vault_root_token

            for secret in self.vault_secrets:
                value = self.env.get(secret)
                if not value:
                    raise ValueError("Environment variable %s required as secret is not defined." % secret)
                if os.path.isfile(os.path.expanduser(value)):
                    with open(os.path.expanduser(value), 'r') as f:
                        value = f.read()
                client.write('secret/%s' % secret, value=value)
            service.options['build']['args']['VAULT_TOKEN'] = token
            service.options['build']['args']['VAULT_ADDR'] = 'http://%s:%s' % (
                self.vault_build_host, self.vault_port
            )

    def cleanup(self):
        client = hvac.Client(
            url="http://%s:%s" % (self.vault_host, self.vault_port),
            token=self.vault_root_token
        )
        for token in self.tokens:
            client.revoke_token(token)

