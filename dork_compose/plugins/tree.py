import dork_compose.plugin
from functools import partial
import os


def __filter(blacklist=(), segment=''):
    return len(segment) and segment not in blacklist


def __path(root, path):
    """
    :type root: str
    :type path: str
    """
    return path.replace(root, '').split('/')


def segments(root, path, blacklist):
    """
    :type root: str
    :type path: str
    :type blacklist: list[str]
    """
    return filter(partial(__filter, blacklist), __path(root, path))


class Plugin(dork_compose.plugin.Plugin):
    def environment(self):
        root = os.path.expanduser(self.env.get('DORK_TREE_ROOT', '/var/source'))
        blacklist = self.env.get('DORK_TREE_BLACKLIST', 'feature;hotfix;release')
        path = map(lambda s: s.lower(), segments(root, self.basedir, blacklist.split(';')))
        return {
            'DORK_TREE_ROOT': root,
            'DORK_TREE_BLACKLIST': blacklist,
            'DORK_PROJECT': path[0] if path else 'default',
            'DORK_INSTANCE': '--'.join(path[1:] if path else ['default'])
        }

    def info(self, project):
        return {
            'Project': self.environment()['DORK_PROJECT'],
            'Instance': self.environment()['DORK_INSTANCE'],
        }

