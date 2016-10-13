import dork_compose.plugin
import os


class Plugin(dork_compose.plugin.Plugin):

    def environment(self):
        return {
            'DORK_UID': self.uid,
            'DORK_GID': self.uid,
        }

    @property
    def uid(self):
        return self.env.get('DORK_UID', os.getuid())

    @property
    def gid(self):
        return self.env.get('DORK_GID', self.uid)

    def creating_container(self, service):
        if 'user' not in service.options:
            service.options['user'] = '%s:%s' % (self.uid, self.gid)

