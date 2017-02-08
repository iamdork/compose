import dork_compose.plugin
import os
import shutil
from dork_compose.helpers import is_subdir

import six
import sys
from compose.progress_stream import stream_output, StreamOutputError
from compose.service import BuildError, NoSuchImageError
from docker.errors import NotFound


class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name, command):
        super(Plugin, self).__init__(env, name, command)
        self.clean_paths = []

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

        if not onbuild and context and not is_subdir(context, self.env['DORK_SOURCE']):
            dockerfile = service.options.get('build', {}).get('dockerfile', None)

            onbuild = "%s/%s:autobuild" % (
                os.path.basename(self.env.get('DORK_LIBRARY', self.project)),
                service.name
            )

            build_output = service.client.build(
                path=context,
                tag=onbuild,
                pull=pull,
                forcerm=force_rm,
                nocache=no_cache,
                dockerfile=dockerfile,
            )
            try:
                stream_output(build_output, sys.stdout)
            except StreamOutputError as e:
                raise BuildError(self, six.text_type(e))

        if onbuild:
            self.clean_paths.append(source)
            dockerfile = '%s/Dockerfile' % source
            dockerignore = '%s/.dockerignore' % source

            if os.path.isfile(dockerfile):
                os.rename(dockerfile, '%s/.dork.Dockerfile' % source)

            if os.path.isfile(dockerignore):
                shutil.copyfile(dockerignore, '%s/.dork.dockerignore' % source)
            else:
                open('%s/.dockerignore' % source, 'a').close()

            with open(dockerfile, 'w') as f:
                # TODO: don't rely on virtualport
                # proxy plugin should not modify config so we can use real ports
                virtual_port = service.options.get('environment', {}).get('VIRTUAL_PORT', None)
                if virtual_port:
                    f.write('FROM %s \nLABEL dork.source="%s"\nEXPOSE %s' % (onbuild, source, virtual_port))
                else:
                    f.write('FROM %s \nLABEL dork.source="%s"' % (onbuild, source))

            try:
                image = service.client.inspect_image(onbuild)
            except NotFound:
                service.client.pull(onbuild)
                image = service.client.inspect_image(onbuild)

            dependencies = (filter(lambda x: x, image.get('Config', {})
                                   .get('Labels', {})
                                   .get('dork.dependencies', '')
                                   .split(';')))

            if isinstance(service.options.get('labels'), dict) and 'dork.dependencies' in service.options['labels']:
                dependencies = service.options.get('labels').get('dork.dependencies', '').split(';')

            with open(dockerignore, 'a') as f:
                f.write('\n' + '\n'.join(dependencies))

            service.options['build']['context'] = os.path.abspath(source)

    def cleanup(self):
        for path in self.clean_paths:
            if os.path.isfile('%s/.dork.Dockerfile' % path):
                os.remove('%s/Dockerfile' % path)
                os.rename('%s/.dork.Dockerfile' % path, '%s/Dockerfile' % path)
            elif os.path.isfile('%s/Dockerfile' % path):
                os.remove('%s/Dockerfile' % path)
            if os.path.isfile('%s/.dork.dockerignore' % path):
                os.remove('%s/.dockerignore' % path)
                os.rename('%s/.dork.dockerignore' % path, '%s/.dockerignore' % path)
            elif os.path.isfile('%s/.dockerignore' % path):
                os.remove('%s/.dockerignore' % path)
