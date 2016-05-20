import dork.plugin
import os
import shutil
import tempfile


class Plugin(dork.plugin.Plugin):
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

    @property
    def source(self):
        return self.env.get('DORK_LIBRARY_SOURCE', 'source')

    def info(self):
        return {
            'Library': self.library
        }

    def building_service(self, service):
        # Assemble the full build context for our service.
        dirname = tempfile.mktemp()
        self.tempdirs.append(dirname)
        shutil.copytree(service.options['build']['context'], dirname)
        # TODO: find a faster solution
        # Perhaps there is a better option than a full source directory copy?
        # Docker does not allow symlinks
        # - hardlinks?
        # - rsync?
        # - mounting if possible?
        shutil.copytree(self.basedir, '%s/%s' % (dirname, self.source))
        service.options['build']['context'] = dirname
        dork.plugin.Plugin.building_service(self, service)

    def cleanup(self):
        for d in self.tempdirs:
            shutil.rmtree(d)
