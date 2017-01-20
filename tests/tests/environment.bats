#!/usr/bin/env bats

load common

@test "Environment variable replacement." {
  cd sources/environment/a
  export WHATISIT="a test"

  dork-compose up -d

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the container is accessible.
  get a.dork | grep '<h1>This is a test.</h1>'

  dork-compose down -v --rmi local
}


@test "Environment precedence." {
  cd sources/environment/a
  export WHATISIT="a test"
  export ENVIRONMENT_TEST="This override will not work."
  dork-compose up -d

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the container is accessible.
  get a.dork | grep '<h1>This is a test.</h1>'

  dork-compose down -v --rmi local
}
