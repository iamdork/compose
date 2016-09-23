# Dork Compose
![Build Status](https://travis-ci.org/iamdork/compose.svg?branch=master)

## What is this?
`dork-compose` is a drop in replacement for the [docker-compose] command line tool, adding some convenience features for running multiple compose projects on the same host.

- Volume snapshots with automatic versioning.
- Separation of Docker setup (`Dockerfile` and `docker-compose.yml`) from application source code.
- Automatic launch of and connection to auxiliary services, like [nginx](https://github.com/jwilder/nginx-proxy)- or [XDebug](https://xdebug.org/docs-dbgp.php#just-in-time-debugging-and-debugger-proxies) proxies.

### Example use cases:
- Your local development workstation, hosting multiple different projects built on the same framework, and therefore requiring similar infrastructure and setup steps.
- A staging server running multiple versions of the same project, doing fast upgrade testing by using volume snapshots.
- A continuous integration server, running automatic tests on pull requests.


## Installation
`dork-compose` uses the same installation procedures as [docker-compose].
Either using pip:
```
$ pip install dork-compose
```

Or by installing it as a container itself.

```bash
$ curl -L https://raw.githubusercontent.com/iamdork/compose/master/run.sh > /usr/local/bin/dork-compose
$ chmod +x /usr/local/bin/dork-compose
```

## Plugins

Everything `dork-compose` does additionally to `docker-compose` is implemented
using plugins. The `DORK_PLUGINS` environment variable controls which plugins
are loaded and in which order they are executed. Plugins are able to alter
environment variables, modify the configuration from `docker-compose.yml` and
act on certain events throughout the `docker-compose` command processes.

By default the `DORK_PLUGINS` variable looks like this:

```
env:multi:lib:autobuild:hotcode:dependencies:filesystem:proxy:dns:vault
```

That's the default workstation setup. Plugins are executed from left to right.
If two plugins to the same, the right one wins.  
Let's run through this example:

- **env:** Scans parent directories for `.env` or `.dork.env` files and
  populates the environment with their contents.
  
- **multi:** Multiple different projects. The project name will be the name of
  the containing directory. It is used to prefix snapshots and build the domain.

- **lib:** If there is a `DORK_LIBRARY` environment variable that contains a
  valid directory, `dork-compose` will assume the `docker-compose.yml` is there.
  The current application sources will be added to the `Dockerfile` build context
  automatically.
  
- **autbuild:** Automatically includes the current source directory in the build
  context.

- **hotcode:** Mount code directories you work on into your local codebase.

- **dependencies:** Syncs sources downloaded during the build process (e.g. the
  composer `vendor` directory) to your local environment. For debugging and IDE
  autocompletion.

- **filesystem:** Implements snapshots as plain rsync. Not particularly fast or
  disk space economic, but works out of the box everywhere.

- **proxy:** Spins up a proxy service that serves your project at
  http://project.dork.io.
  
- **dns:** Runs a dns server and configures your system to use it. Enables you
  to use the domain `dork.io`.
 
- **vault:** Exposes secrets (e.g. the github private token) to the build
  process without leaving any traces in the image.

There are no configuration files. Plugins can be configured using environment
variables, which you define in your shell environment for by using the **env**
plugin. For a complete list of plugins and their options please refer to
[Appendix: Plugins][]. For an in-action example of these plugins, please refer
to the [drupal-simple](https://github.com/iamdork/recipes/tree/master/drupal-simple)
in the [recipes repository](https://github.com/iamdork/recipes).


### Custom plugins

It's possible to create and load custom plugins. Simply create a Python file
with one class called *Plugin* that extends `dork_compose.plugin.Plugin` and
attach it to the `DORK_PLUGINS` variable:

```
env:multi:lib:autobuild:hotcode:dependencies:filesystem:proxy:dns:vault:my_plugin=~/path/to/myplugin.py
```

For example plugins have a look at the `plugins` directory inside the `dork-compose` source.

## Snapshots

`dork-compose` is able to create snapshots of all data volumes used in a compose
project. This is done by using the additional `dork-compose snapshot` command.
For an example of how to work with snapshots, please refer to the
*drupal-simple* example in the [examples repository](https://github.com/iamdork/examples).

### Projects & Instances

Snapshots are organized in  *projects* and *instances*. `dork-compose` assumes
that instances of the same project are compatible. Aside from building the proxy
domain, the major purpose is to restrict snapshots to be used by instances of
the same project only.

The current *project* and *instance* is determined by plugins (like *multi* in
the default setup) or by the `DORK_PROJECT` and `DORK_INSTANCE` environment
variables.

### Automatic snapshots

If the snapshot identifier is omitted from the `snapshot save` and
`snapshot load` command, `dork-compose` will rely on plugins to provide one.
The **git** plugin in the default setup for example will store snapshots by the
current HEAD hash and will try to load the closest available ancestor to the
current checkout. This avoids breaking your development database by switching
between feature branches.

## Appendix: Plugins

*TODO: explain all builtin plugins.*
[docker-compose]: https://docs.docker.com/compose/
[env]: https://docs.docker.com/compose/compose-file/#env-file
