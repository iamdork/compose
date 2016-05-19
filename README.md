# Dork Compose

## What is this?

`dork-compose` is a drop in replacement for the [docker-compose]
command line tool, adding some convenience features for running
multiple compose projects on the same host.

- Volume snapshots with automatic versioning.
- HTTP proxy management.
- Separation of Docker setup (`Dockerfile` and `docker-compose.yml`)
  from application source code.

### Example use cases:
- Your local development workstation, hosting multiple different
  projects built on the same framework, and therefore requiring
  similar infrastructure and setup steps.
- A staging server running multiple versions of the same project,
  doing fast upgrade testing by using volume snapshots.
- A continuous integration server, running automatic tests on
  pull requests.


## Installation
`dork-compose` uses the same installation procedures as
[docker-compose].
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

Everything `dork-compose` does additionally to `docker-compose` is
implemented using plugins. The `DORK_PLUGINS` environment variable
controls which plugins are loaded and in which order they are
executed. Plugins are able to alter environment variables, modify
the configuration from `docker-compose.yml` and act on certain
events throughout the `docker-compose` command processes.

By default the `DORK_PLUGINS` variable looks like this:

```
env:lib:multi:git:filesystem:proxy
```

That's the default workstation setup. Plugins are executed from
left to right. If two plugins to the same, the right one wins.
Let's run through this example:

**env**
:   Searches for [.env files][env] in the current and all parent
    directories and merges their content into the environment.

**lib**
:   If there is a `DORK_LIBRARY` environment variable that
    contains a valid directory, `dork-compose` will assume the
    `docker-compose.yml` is there.

**multi**
:   Multiple different projects. The project name will be the
    name of the containing directory. It is used to prefix
    snapshots and build the domain.

**git**
:   Git repository information is used to handle automatic *save*
    and *load* of snapshots. Handy for frequent branch switchers.

**filesystem**
:   Implements snapshots as plain filesystem copy operations. Not
    particularly fast or disk space economic, but works
    out of the box everywhere.

**proxy**
:   Spins up a proxy service that serves your project at
    http://project.127.0.0.1.xip.io.

There are no configuration files. Plugins can be configured using
environment variables, which you define in your shell environment
for by using the first **env** plugin. For a complete list of
plugins and their options please refer to [Appendix: Plugins][].


### Custom plugins

It's possible to create and load custom plugins. Simply create a
Python file with one class called *Plugin* that extends
`dork.plugin.Plugin` and attach it to the `DORK_PLUGINS` variable:

```
env:lib:multi:git:filesystem:proxy:my_plugin=~/path/to/myplugin.py
```

For example plugins have a look at the `plugins` package inside the
`dork-compose` source.

## Snapshots

`dork-compose` is able to create snapshots of all data volumes
used in a compose project. This is done by using the additional
`dork-compose snapshot` command.

**Example:**
Let's assume your project defines two data volumes. One for the
database (`db`), the other one for uploaded files (`files`).
Setup and install the application as usual. After adding test data
run `dork-compose snapshot save my_snapshot` to store all runtime
information in a snapshot.
The next time you want to set up a new instance of this project,
for example for feature branch without messing up your current
database, you just start the project with `dork-compose up` and
run `dork-compose snapshot load my_snapshot`. The previously saved
database and uploaded files are immediately ready to go. No setup
or install process.

### Projects & Instances

This example already introduced the concept of *projects* and
*instances*. `dork-compose` assumes that instances of the same
project are compatible. Aside from building the proxy domain,
the major purpose is to restrict snapshots to be used by
instances of the same project only.

The current *project* and *instance* is determined by plugins
(like *multi* in the default setup) or by the `DORK_PROJECT`
and `DORK_INSTANCE` environment variables.

### Automatic snapshots

If the snapshot identifier is omitted from the `snapshot save`
and `snapshot load` command, `dork-compose` will rely on
plugins to provide one. The **git** plugin in the default
setup for example will store snapshots by the current HEAD
hash and will try to load the closest available ancestor to
the current checkout. This avoids breaking your development
database by switching between feature branches.

## Appendix: Plugins

[docker-compose]: https://docs.docker.com/compose/
[env]: https://docs.docker.com/compose/compose-file/#env-file