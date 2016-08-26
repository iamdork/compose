import dork_compose.plugin
import os

import six
import sys
from compose.progress_stream import stream_output, StreamOutputError
from compose.service import BuildError


class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name):
        super(Plugin, self).__init__(env, name)
        self.dorkerfiles = []

    def alter_config_schema(self, schema):
        schema['definitions']['service']['properties']['build']['oneOf'][1]['properties'].update({
            'source': {'type':'string'},
            'onbuild': {'type':'string'},
        })

        schema['definitions']['constraints']['service']['properties']['build'] = {
            'anyOf': [
                {'required': ['context']},
                {'required': ['onbuild']},
            ]
        }

    def building(self, service, no_cache, pull, force_rm):
        context = service.options.get('build', {}).get('context', None)
        source = service.options.get('build', {}).get('source', '.')
        onbuild = service.options.get('build', {}).get('onbuild', None)

        if not onbuild and context and not context.startswith(self.env['DORK_SOURCE']):
            dockerfile = service.options.get('build', {}).get('dockerfile', None)
            args = service.options.get('build', {}).get('args', {})

            onbuild = "autobuild/%s:%s-onbuild" % (self.project, service.name)

            build_output = service.client.build(
                path=context,
                tag=onbuild,
                pull=pull,
                forcerm=force_rm,
                nocache=no_cache,
                dockerfile=dockerfile,
                buildargs=args,
            )
            try:
                stream_output(build_output, sys.stdout)
            except StreamOutputError as e:
                raise BuildError(self, six.text_type(e))

        if onbuild:
            dorkerfile = '%s/.dorkerfile' % source
            self.dorkerfiles.append(dorkerfile)
            with open(dorkerfile, 'w') as f:
                f.write('FROM %s \nLABEL dork.source="%s"' % (onbuild, source))
            service.options['build']['context'] = os.path.abspath(source)
            service.options['build']['dockerfile'] = '.dorkerfile'

    def cleanup(self):
        for dorkerfile in self.dorkerfiles:
            os.remove(dorkerfile)
