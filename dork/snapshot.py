from dork.environment import env, repository_path

import dork.snapshot_managers.simple
from compose.volume import ProjectVolumes
from git import Repo
from gitdb.exc import BadName
from functools import partial


@env('DORK_SNAPSHOT_MANAGER')
def snapshot_manager():
    return 'simple'

_manager = {
    'simple': dork.snapshot_managers.simple
}[snapshot_manager()]


def __commit(repo, hash):
    try:
        return repo.commit(hash)
    except BadName:
        return None


class DorkVolumes(ProjectVolumes):

    def initialize(self):
        _manager.initialize()
        return super(DorkVolumes, self).initialize()

    def remove(self):
        super(DorkVolumes, self).remove()
        _manager.remove()


def save(name):
    if not name:
        name = Repo(repository_path()).head.commit.hexsha
    _manager.save(name)


def load(name):
    if not name:
        repo = Repo(repository_path())
        head = repo.head.commit
        distance = -1
        for commit in filter(lambda x: x, map(partial(__commit, repo), _manager.ls())):
            if repo.is_ancestor(commit.hexsha, head.hexsha):
                diff = len(commit.diff(head))
                if diff < distance or distance == -1:
                    name = commit.hexsha
                    distance = diff

    _manager.load(name)


def ls():
    for snapshot in _manager.ls():
        print(snapshot)


def reset():
    _manager.reset()


def rm(names):
    if not names:
        # If no specific snapshot is defined, remove just clean unused ones.
        repo = Repo(repository_path())
        snapshots = filter(lambda x: x, map(partial(__commit, repo), __manager.ls()))
        names = []
        for current in snapshots:
            for test in snapshots:
                if repo.is_ancestor(test, current) and test != current and test.hexsha not in names:
                    names.append(test.hexsha)

    for name in names:
        _manager.rm(name)


def process_config(conf):
    return _manager.process_config(conf)
