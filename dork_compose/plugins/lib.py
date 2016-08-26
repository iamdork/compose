import dork_compose.plugin
import os

from compose.config.environment import env_vars_from_file


class Plugin(dork_compose.plugin.Plugin):

    @property
    def libraries(self):
        libs = filter(lambda x: len(x), self.env.get('DORK_LIBRARY', '').split(';'))
        return ['/'.join(filter(lambda x: len(x), [
            os.path.expanduser(self.env.get('DORK_LIBRARY_PATH', '')),
            os.path.expanduser(lib),
        ])) for lib in libs]

    def environment(self):
        env = {}
        for library in self.libraries:

            files = filter(lambda x: x, self.env.get('COMPOSE_FILE', '').split(':'))
            if os.path.isfile('docker-compose.yml') and not files:
                files.append('docker-compose.yml')
            files.append(library + '/docker-compose.yml')
            env.update({
                'COMPOSE_FILE': ':'.join(files)
            })

            envfile = '%s/.env' % library
            if os.path.isfile(envfile):
                for key, value in env_vars_from_file(envfile).iteritems():
                    if key not in os.environ:
                        env[key] = os.path.expandvars(value)
        return env



