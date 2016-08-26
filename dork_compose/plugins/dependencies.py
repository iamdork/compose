import dork_compose.plugin
import tempfile
from tarfile import TarFile
import os
import shutil


class Plugin(dork_compose.plugin.Plugin):

    def initialized(self, project, containers=None):
        source = self.env.get('DORK_SOURCE')
        for container in containers:
            root = container.labels.get('dork.root', None)
            dsource = container.labels.get('dork.source', '.')
            deps = filter(lambda x: x, container.labels.get('dork.dependencies', '').split(';'))
            if root:
                for path in deps:
                    src = '/'.join([root, path])
                    dst = '/'.join([source, dsource, path])
                    print "Synching %s to %s." % (src, dst)
                    tmp = tempfile.NamedTemporaryFile(delete=False)
                    container.client.exec_start(container.client.exec_create(container.id, "mkdir -p %s" % src))
                    response, info = container.client.get_archive(container.id, src)
                    for chunk in response.stream(1024):
                        tmp.write(chunk)
                    tmp.close()
                    tar = TarFile.open(tmp.name)
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    tar.extractall(os.path.dirname(dst))


