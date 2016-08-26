import dork_compose.plugin
import os

from compose.config.environment import env_vars_from_file


class Plugin(dork_compose.plugin.Plugin):

    @property
    def library(self):
        return '/'.join(filter(lambda x: len(x), [
            os.path.expanduser(self.env.get('DORK_LIBRARY_PATH', '')),
            os.path.expanduser(self.env.get('DORK_LIBRARY', '')),
        ]))

    def environment(self):
        env = {}
        if self.library:

            files = filter(lambda x: x, self.env.get('COMPOSE_FILE', '').split(':'))
            if os.path.isfile('docker-compose.yml') and not files:
                files.append('docker-compose.yml')
            files.append(self.library + '/docker-compose.yml')
            env.update({
                'COMPOSE_FILE': ':'.join(files)
            })
            envfile = '%s/.dork.env' % self.library
            if os.path.isfile(envfile):
                for key, value in env_vars_from_file(envfile).iteritems():
                    env[key] = os.path.expandvars(value)
            envfile = '%s/.env' % self.library
            if os.path.isfile(envfile):
                for key, value in env_vars_from_file(envfile).iteritems():
                    env[key] = os.path.expandvars(value)
        return env



