import dork_compose.plugin
import platform
import pkg_resources
from subprocess import call
import tempfile

class Plugin(dork_compose.plugin.Plugin):

    def environment(self):
        return {
            'DORK_DNS_PORT': "53",
            'DORK_PROXY_DOMAIN': "dork",
        }

    @property
    def auxiliary_project(self):
        return pkg_resources.resource_filename('dork_compose', 'auxiliary/dns')

    def initializing(self, project, service_names=None):
        if platform.system() == "Darwin":
            content = "domain %s\nnameserver127.0.0.1\n" % self.env.get('DORK_PROXY_DOMAIN')
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.write(content)
            tmp.close()
            call(['sudo', 'cp', tmp.name, '/etc/resolver/%s' % self.env.get('DORK_PROXY_DOMAIN')])
            call(['sudo', 'chmod', '664', '/etc/resolver/%s' % self.env.get('DORK_PROXY_DOMAIN')])
            call(['sudo', 'killall', 'mDNSResponder'])
            pass

        if platform.system() == "Linux":
            # TODO: add support for :inux
            pass
