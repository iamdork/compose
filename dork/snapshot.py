from dork.environment import env, repository_path

import dork.snapshot_managers.simple
from git import Repo
from gitdb.exc import BadName


@env('DORK_SNAPSHOT_MANAGER')
def snapshot_manager():
    return 'simple'

__manager = {
    'simple': dork.snapshot_managers.simple
}[snapshot_manager()]


def initialize():
    __manager.initialize()


def save(name):
    if not name:
        name = Repo(repository_path()).head.commit.hexsha
    __manager.save(name)


def load(name):
    if not name:
        repo = Repo(repository_path())
        head = repo.head.commit
        distance = -1
        for snapshot in __manager.ls():
            try:
                commit = repo.commit(snapshot)
            except BadName:
                continue

            if repo.is_ancestor(commit.hexsha, head.hexsha):
                diff = len(repo.commit(snapshot).diff(repo.commit(head)))
                if diff < distance or distance == -1:
                    name = commit.hexsha
                    distance = diff

    __manager.load(name)


def ls():
    for snapshot in __manager.ls():
        print(snapshot)


def clear():
    __manager.clear()


def process_config(conf):
    return __manager.process_config(conf)
