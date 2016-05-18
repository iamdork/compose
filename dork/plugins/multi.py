import dork.plugin


class Plugin(dork.plugin.Plugin):
    def environment(self):
        return {
            'DORK_PROJECT': self.basedir.split('/')[-1]
        }
