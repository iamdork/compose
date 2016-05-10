import os
__env = {}


def env(name):
    def real(func):
        def wrap(*args, **kwargs):
            return os.environ.get(name, func(*args, **kwargs))
        __env[name] = wrap
        return wrap
    return real


def initialize():
    """
    Initialize environment variables.
    """
    os.environ.update({key: func() for key, func in __env.iteritems()})


def __path(root, directory):
    return filter(len, directory.replace(root, '').split('/'))


@env('DORK_REPOSITORY_PATH')
def repository_path():
    return os.path.abspath(os.path.curdir)


@env('DORK_ROOT_PATH')
def root_path():
    return '/var/source'


@env('DORK_PROJECT')
def project():
    return __path(root_path(), repository_path())[0]


@env('DORK_INSTANCE')
def instance():
    return __path(root_path(), repository_path())[-1]
