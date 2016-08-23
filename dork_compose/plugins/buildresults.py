import dork_compose.plugin
import tempfile
from tarfile import TarFile
import os
import shutil


class Plugin(dork_compose.plugin.Plugin):

    def initialized(self, project, containers=None):
        super(Plugin, self).initialized(project, containers)
        source = self.env.get('DORK_SOURCE')
        for container in containers:
            if 'dork.buildresults.paths' in container.labels and 'dork.buildresults.root' in container.labels:
                root = container.labels['dork.buildresults.root']
                paths = filter(lambda x: x, container.labels['dork.buildresults.paths'].split(';'))
                for path in paths:
                    print "Synching %s." % path
                    tmp = tempfile.NamedTemporaryFile(delete=False)
                    container.client.exec_start(container.client.exec_create(container.id, "mkdir -p %s/%s" % (root, path)))
                    response, info = container.client.get_archive(container.id, "%s/%s" % (root, path))
                    for chunk in response.stream(1024):
                        tmp.write(chunk)
                    tmp.close()
                    tar = TarFile.open(tmp.name)
                    if os.path.isdir("%s/%s" % (source, path)):
                        shutil.rmtree("%s/%s" % (source, path))
                    tar.extractall(os.path.dirname("%s/%s" % (source, path)))


