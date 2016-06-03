import dork_compose.plugin
from compose.config.config import VolumeSpec


class Plugin(dork_compose.plugin.Plugin):
    @property
    def paths(self):
        return filter(lambda x: x, self.env.get('DORK_HOT_CODE_PATHS', '').split(';'))

    def preprocess_config(self, config):
        for service in config.services:
            if 'environment' in service and 'DORK_SOURCE_PATH' in service['environment'] and 'DORK_SOURCE_ROOT' in service['environment']:
                src = self.env['DORK_SOURCE']
                dst = service['environment']['DORK_SOURCE_ROOT']
                for path in self.paths:
                    if 'volumes' not in service:
                        service['volumes'] = []
                    service['volumes'].append(VolumeSpec.parse('%s/%s:%s/%s' % (
                        src, path, dst, path
                    )))

