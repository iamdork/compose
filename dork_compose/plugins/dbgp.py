import dork_compose.plugin
import pkg_resources


class Plugin(dork_compose.plugin.Plugin):

    def environment(self):
        return {
            'DORK_DBGP_NAME': self.env.get('DORK_DBGP_NAME', 'dork_aux_dbgp')
        }

    @property
    def auxiliary_project(self):
        return pkg_resources.resource_filename('dork_compose', 'auxiliary/dbgp')
