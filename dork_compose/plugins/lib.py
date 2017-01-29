import dork_compose.plugin
import os
import glob
import dork_compose.helpers

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
        layout = self.env.get('DORK_DIRECTORY_LAYOUT', False)
        source = self.env.get('DORK_SOURCE')
        if layout:
            matches = [path for path in glob.glob(os.path.abspath(layout)) if dork_compose.helpers.is_subdir(source, path)]
            if not matches:
                return env
            env['DORK_SOURCE'] = max(matches, key=len)
            if env['DORK_SOURCE'] != source:
                hotcode = [path for path in env.get('DORK_HOTCODE', '').split(';') if path != '']
                hotcode.append(source[len(env['DORK_SOURCE'])+1:])
                env['DORK_HOTCODE'] = ';'.join(hotcode)

        if self.library:
            files = filter(lambda x: x, self.env.get('COMPOSE_FILE', '').split(':'))
            if os.path.isfile(self.library + '/docker-compose.yml'):
                files.insert(0, self.library + '/docker-compose.yml')

            os.environ.update({
                'COMPOSE_FILE': ':'.join(files)
            })

            envfile = '%s/.env' % self.library
            if os.path.isfile(envfile):
                for key, value in env_vars_from_file(envfile).iteritems():
                    if key not in self.env:
                        env[key] = os.path.expandvars(value)
        return env



