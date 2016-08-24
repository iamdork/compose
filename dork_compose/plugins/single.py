import dork_compose.plugin


class Plugin(dork_compose.plugin.Plugin):
    def get_instance(self):
        return self.basedir.split('/')[-1]
    def get_project(self):
        return 'default'

    def environment(self):
        return {
            'DORK_PROJECT': self.get_project(),
            'DORK_INSTANCE': self.get_instance()
        }

    def info(self, project):
        return {
            'Project': self.get_project(),
            'Instance': self.get_instance()
        }
