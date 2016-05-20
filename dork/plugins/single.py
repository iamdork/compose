import dork.plugin


class Plugin(dork.plugin.Plugin):
    def get_instance(self):
        return self.basedir.split('/')[-1]

    def environment(self):
        return {
            'DORK_INSTANCE': self.get_instance()
        }

    def info(self):
        return {
            'Instance': self.get_instance()
        }
