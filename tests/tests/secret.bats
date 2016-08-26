#!/usr/bin/env bats

load common

@test "Build secret test" {
  cd sources/secret

  dork-compose up -d --build

  # Test if the http service is available and running.
  docker ps | grep 'secret_http_1'

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the container is accessible.
  get secret.dork | grep 'The lost art of keeping a secret'

  dork-compose down

  # Test if the http service has been removed.
  ! docker ps -a | grep 'secret_http_1'
}
