import dork_compose.plugin
import os
import shutil
import tempfile


class Plugin(dork_compose.plugin.Plugin):
    def initialize(self):
        self.tempdirs = []
        if self.library:
            os.chdir(os.path.expanduser(self.library))
            return True

    @property
    def library(self):
        return '/'.join(filter(lambda x: len(x), [
            os.path.expanduser(self.env.get('DORK_LIBRARY_PATH', '')),
            os.path.expanduser(self.env.get('DORK_LIBRARY', '')),
        ]))

    def info(self, project):
        return {
            'Library': self.library
        }

    def building_service(self, service):
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
