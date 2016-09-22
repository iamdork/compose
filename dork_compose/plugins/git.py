import dork_compose.plugin
from git import Repo
from gitdb.exc import BadName


class Plugin(dork_compose.plugin.Plugin):

    def __init__(self, env, name, command):
        dork_compose.plugin.Plugin.__init__(self, env, name, command)
        try:
            self.__repo = Repo(self.basedir)
        except Exception:
            self.__repo = False

    def __commit(self, hash):
        if not self.__repo:
            return None
        try:
            return self.__repo.commit(hash)
        except BadName:
            return None

    def snapshot_autosave(self):
        if not self.__repo:
            return None
        return self.__repo.head.commit.hexsha

    def snapshot_autoload(self, snapshots=()):
        if not self.__repo:
            return None
        name = None
        head = self.__repo.head.commit
        distance = -1
        for commit in filter(lambda x: x, map(self.__commit, snapshots)):
            if self.__repo.is_ancestor(commit.hexsha, head.hexsha):
                diff = len(commit.diff(head))
                if diff < distance or distance == -1:
                    name = commit.hexsha
                    distance = diff
        return name

    def snapshot_autoclean(self, snapshots=()):
        if not self.__repo:
            return None
        snapshots = filter(lambda x: x, map(self.__commit, snapshots))
        names = []
        for current in snapshots:
            for test in snapshots:
                if self.__repo.is_ancestor(test, current) and test != current and test.hexsha not in names:
                    names.append(test.hexsha)
        return names

