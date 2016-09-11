import dork_compose.plugin


class Plugin(dork_compose.plugin.Plugin):

    def preprocess_config(self, config):
        config.services.append({
            'name': 'dork_tracker',
            'image': 'alpine:3.4',
            'command': 'tail -f /dev/null',
            'volumes': [],
            'labels': {
                'dork.tracker': '',
                'dork.tracker.source': self.env.get('DORK_SOURCE'),
                'dork.tracker.project': self.env.get('DORK_PROJECT'),
                'dork.tracker.instance': self.env.get('DORK_INSTANCE'),
            }
        })

