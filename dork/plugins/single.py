import dork.plugin


class Plugin(dork.plugin.Plugin):
    def environment(self):
        return {
            'DORK_INSTANCE': self.basedir.split('/')[-1]
        }
