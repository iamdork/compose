import dork.plugin
from functools import partial


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


class Plugin(dork.plugin.Plugin):
    def environment(self):
        root = self.env.get('DORK_TREE_ROOT', '/var/source')
        blacklist = self.env.get('DORK_TREE_BLACKLIST', 'feature;hotfix;release')
        path = segments(root, self.env['DORK_REPOSITORY_PATH'], blacklist.split(';'))
        return {
            'DORK_TREE_ROOT': root,
            'DORK_TREE_BLACKLIST': blacklist,
            'DORK_PROJECT': path[0],
            'DORK_INSTANCE': '/'.join(path[1:])
        }

