import dork_compose.plugin
import os

from compose.config.environment import env_vars_from_file

class Plugin(dork_compose.plugin.Plugin):
    def environment(self):
        old_environment = os.environ.copy()
        path = filter(len, os.path.abspath(os.path.curdir).split('/'))
        current = ''
        while len(path):
            current = current + '/' + path.pop(0)
            envfile = '%s/.dork.env' % current
            if os.path.isfile(envfile):
                for key, value in env_vars_from_file(envfile).iteritems():
                    os.environ[key] = os.path.expandvars(value)
                continue

            envfile = '%s/.env' % current
            if os.path.isfile(envfile):
                for key, value in env_vars_from_file(envfile).iteritems():
                    os.environ[key] = os.path.expandvars(value)
        env = os.environ.copy()
        os.environ = old_environment
        return env


