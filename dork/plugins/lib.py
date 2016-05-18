import dork.plugin
import os
import shutil


class Plugin(dork.plugin.Plugin):
    def initialize(self):
        self.tempfiles = []
        if self.library:
            os.chdir(os.path.expanduser(self.library))

    @property
    def library(self):
        return os.path.expanduser(self.env.get('DORK_LIBRARY', ''))

    def is_delocated(self, build):
        return (
            'context' in build and 'dockerfile' in build
            and not os.path.exists('%s/%s' % (build['context'], build['dockerfile']))
            and os.path.exists('%s/%s' % (self.library, build['dockerfile']))
        )

    def preprocess_config(self, config):
        if not self.library:
            return
        for service in config.services:
            if 'build' in service and self.is_delocated(service['build']):
                src = '%s/%s' % (self.library, service['build']['dockerfile'])
                dest = '%s/%s' % (self.basedir, service['build']['dockerfile'])
                shutil.copy(src, dest)
                self.tempfiles.append(dest)

    def cleanup(self):
        for file in self.tempfiles:
            os.remove(file)
