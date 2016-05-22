import dork_compose.plugin
import os
from compose.config.environment import env_vars_from_file


class Plugin(dork_compose.plugin.Plugin):
    def environment(self):
        # Collect separate environment dict from .env files in
        # current and parent directories.
        env = {}
        path = filter(len, self.basedir.split('/'))
        current = ''
        while len(path):
            current = current + '/' + path.pop(0)
            envfile = '%s/.env' % current
            if os.path.isfile(envfile):
                env.update(env_vars_from_file(envfile))
        return env

    def info(self, project):
        return self.environment()
