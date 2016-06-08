#!/usr/bin/env bats

SOURCES="$(pwd)/sources"
export DORK_LIBRARY_PATH="$(pwd)/lib"

@test "Simple project info" {
  cd sources/simple

  # Check if the url is available in the info.
  dork-compose info | grep 'http://simple.127.0.0.1.xip.io'
}

@test "Simple project accessible" {
  cd sources/simple

  dork-compose up -d

  # Test if the http service is available and running.
  docker ps | grep 'simple_http_1'

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the container is accessible.
  curl http://simple.127.0.0.1.xip.io | grep '<h1>Testpage.</h1>'

  dork-compose down

  # Test if the http service has been removed.
  ! docker ps -a | grep 'simple_http_1'
}
