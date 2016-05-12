#!/bin/bash
# Modified version of https://github.com/docker/compose/blob/master/script/run/run.sh
#
# Run dork-compose in a container
#
# This script will attempt to mirror the host paths by using volumes for the
# following paths:
#   * $(pwd)
#   * $(dirname $COMPOSE_FILE) if it's set
#   * $HOME if it's set
#
# You can add additional volumes (or any docker run options) using
# the $COMPOSE_OPTIONS environment variable.
#


set -e

VERSION="latest"
IMAGE="iamdork/compose:$VERSION"


# Setup options for connecting to docker host
if [ -z "$DOCKER_HOST" ]; then
    DOCKER_HOST="/var/run/docker.sock"
fi
if [ -S "$DOCKER_HOST" ]; then
    DOCKER_ADDR="-v $DOCKER_HOST:$DOCKER_HOST -e DOCKER_HOST"
else
    DOCKER_ADDR="-e DOCKER_HOST -e DOCKER_TLS_VERIFY -e DOCKER_CERT_PATH"
fi

# Dork default variables.
DORK_REPOSITORY_PATH=${DORK_REPOSITORY_PATH:=$(pwd)}
DORK_SNAPSHOT_MANAGER=${DORK_SNAPSHOT_MANAGER:='simple'}

# Pass dork environment variables.
DORK_ENV="-e DORK_ROOT_PATH -e DORK_DOMAIN -e DORK_SUBDOMAIN -e DORK_SNAPSHOT_MANAGER -e DORK_PROJECT -e DORK_INSTANCE"

# Mount the current repository as a volume.
DORK_VOLUMES="-v $DORK_REPOSITORY_PATH:$DORK_REPOSITORY_PATH"

# If we are using the simple snapshot manager, also mount volumes and snapshot directories.
if [ "$DORK_SNAPSHOT_MANAGER" == 'simple' ]; then
  DORK_SIMPLE_VOLUME_PATH=${DORK_SIMPLE_VOLUME_PATH:='/var/dork/volumes'}
  DORK_SIMPLE_SNAPSHOT_PATH=${DORK_SIMPLE_SNAPSHOT_PATH:='/var/dork/snapshots'}

  DORK_VOLUMES="$DORK_VOLUMES -v $DORK_SIMPLE_VOLUME_PATH:$DORK_SIMPLE_VOLUME_PATH"
  DORK_VOLUMES="$DORK_VOLUMES -v $DORK_SIMPLE_SNAPSHOT_PATH:$DORK_SIMPLE_SNAPSHOT_PATH"
  DORK_ENV="$DORK_ENV -e DORK_SIMPLE_VOLUME_PATH -e DORK_SIMPLE_SNAPSHOT_PATH"
fi


# Setup volume mounts for compose config and context
if [ "$(pwd)" != '/' ]; then
    VOLUMES="-v $(pwd):$(pwd)"
fi
if [ -n "$COMPOSE_FILE" ]; then
    compose_dir=$(dirname $COMPOSE_FILE)
fi
# TODO: also check --file argument
if [ -n "$compose_dir" ]; then
    VOLUMES="$VOLUMES -v $compose_dir:$compose_dir"
fi
if [ -n "$HOME" ]; then
    VOLUMES="$VOLUMES -v $HOME:$HOME -v $HOME:/root" # mount $HOME in /root to share docker.config
fi

# Only allocate tty if we detect one
if [ -t 1 ]; then
    DOCKER_RUN_OPTIONS="-t"
fi
if [ -t 0 ]; then
    DOCKER_RUN_OPTIONS="$DOCKER_RUN_OPTIONS -i"
fi

exec docker run --rm $DOCKER_RUN_OPTIONS $DOCKER_ADDR $COMPOSE_OPTIONS $DORK_ENV $VOLUMES $DORK_VOLUMES -w "$(pwd)" $IMAGE "$@"
