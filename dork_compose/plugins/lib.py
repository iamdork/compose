import dork_compose.plugin
import os
import shutil
import tempfile
import re
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
                self.env[key] = os.path.expandvars(self.env.get(key, value))

        filename = '%s/.dork.env' % self.library
        if os.path.isfile(filename):
            for key, value in env_vars_from_file(filename).iteritems():
                self.env[key] = os.path.expandvars(self.env.get(key, value))
        return self.env

    def info(self, project):
        return {
            'Library': self.library
        }

    def preprocess_config(self, config):
        super(Plugin, self).preprocess_config(config)
        for service in config.services:
            if 'image' in service and re.search('-onbuild$', service['image']):
                service['build']['context'] = self.env.get('DORK_SOURCE')
                service['build']['onbuild'] = service['image']
                service['image'] = "%s/%s:%s" % (self.project, service['name'], self.instance)

    def building(self, service):

        # TODO: find a faster solution
        # Perhaps there is a better option than a full source directory copy?
        # Docker does not allow symlinks
        # - hardlinks?
        # - rsync?
        # - mounting if possible?

        tempdir = tempfile.mktemp()
        self.tempdirs.append(tempdir)
        if service.options['build']['context'] == self.env.get('DORK_SOURCE') and 'onbuild' in service.options['build']:
            # Assemble the full build context for our service.
            shutil.copytree(self.basedir, tempdir, symlinks=True, ignore=lambda *args, **kwargs: ['.git'])
            with open("%s/Dockerfile" % tempdir, "w+") as f:
                f.write("FROM %s" % service.options['build']['onbuild'])
            del service.options['build']['onbuild']
            service.options['build']['context'] = tempdir

        if 'environment' in service.options and 'DORK_SOURCE_PATH' in service.options['environment']:
            # Assemble the full build context for our service.
            shutil.copytree(service.options['build']['context'], tempdir, symlinks=True, ignore=lambda *args, **kwargs: ['.git'])
            shutil.copytree(self.basedir, '%s%s' % (tempdir, service.options['environment']['DORK_SOURCE_PATH']), symlinks=True, ignore=lambda *args, **kwargs: ['.git'])
            service.options['build']['context'] = tempdir

    def cleanup(self):
        for d in self.tempdirs:
            shutil.rmtree(d, ignore_errors=True)
