#!/usr/bin/env bats

load common

@test "Test authorization info" {
  cd sources/auth

  dork-compose info | grep 'password protected'
}


@test "Test authorization login" {
  cd sources/auth

  dork-compose up -d

  # Test if the container started
  docker ps | grep 'auth_http_1'

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the container is accessible using no login.
  curl -I --resolve auth.dork:80:127.0.0.1 http://auth.dork | grep '401 Unauthorized'

  # Test if the container is accessible using no login.
  curl -u dork:dork --resolve auth.dork:80:127.0.0.1 http://auth.dork | grep '<h1>Testpage.</h1>'

  dork-compose down

  # Test if the http service has been removed.
  ! docker ps -a | grep 'simple_http_1'

}
