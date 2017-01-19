#!/usr/bin/env bats

load common

@test "Simple project info" {
  cd sources/simple

  # Check if the url is available in the info.
  dork-compose info | grep 'http://simple.dork'
}

@test "Simple project accessible" {
  cd sources/simple

  dork-compose up -d

  # Test if the http service is available and running.
  docker ps | grep 'simple_http_1'

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the container is accessible.
  get simple.dork | grep '<h1>Testpage.</h1>'

  dork-compose down

  # Test if the http service has been removed.
  ! docker ps -a | grep 'simple_http_1'

  # Test if the proxy has been removed too.
  ! docker ps -a | grep 'proxy'
}
