import dork_compose.plugin
import os
import shutil
import tempfile
from compose.config.environment import env_vars_from_file


class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name):
        dork_compose.plugin.Plugin.__init__(self, env, name)
        self.tempdirs = []
        if self.library:
            os.chdir(self.library)

    @property
    def library(self):
        return '/'.join(filter(lambda x: len(x), [
            os.path.expanduser(self.env.get('DORK_LIBRARY_PATH', '')),
            os.path.expanduser(self.env.get('DORK_LIBRARY', '')),
        ]))

    def environment(self):
        filename = '%s/.env' % self.library
        if os.path.isfile(filename):
            for key, value in env_vars_from_file(filename).iteritems():
                self.env[key] = self.env.get(key, value)
        return self.env

    def info(self, project):
        return {
            'Library': self.library
        }

    def building(self, service):
        if 'environment' in service.options and 'DORK_SOURCE_PATH' in service.options['environment']:
            # Assemble the full build context for our service.
            dirname = tempfile.mktemp()
            self.tempdirs.append(dirname)
            shutil.copytree(service.options['build']['context'], dirname, symlinks=True, ignore=lambda *args, **kwargs: ['.git'])
            # TODO: find a faster solution
            # Perhaps there is a better option than a full source directory copy?
            # Docker does not allow symlinks
            # - hardlinks?
            # - rsync?
            # - mounting if possible?
            shutil.copytree(self.basedir, '%s%s' % (dirname, service.options['environment']['DORK_SOURCE_PATH']), symlinks=True, ignore=lambda *args, **kwargs: ['.git'])
            service.options['build']['context'] = dirname

    def cleanup(self):
        for d in self.tempdirs:
            shutil.rmtree(d)
