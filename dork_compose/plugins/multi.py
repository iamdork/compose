import dork_compose.plugin


class Plugin(dork_compose.plugin.Plugin):
    def environment(self):
        return {
            'DORK_PROJECT': self.get_project()
        }

    def get_project(self):
        return self.basedir.split('/')[-1]

    def info(self):
        return {
            'Project': self.get_project()
        }

