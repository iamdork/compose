import dork_compose.plugin


class Plugin(dork_compose.plugin.Plugin):
    def get_instance(self):
        return self.basedir.split('/')[-1]

    def environment(self):
        return {
            'DORK_INSTANCE': self.get_instance()
        }

    def info(self, project):
        return {
            'Instance': self.get_instance()
        }
