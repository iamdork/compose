#!/usr/bin/env bats

load common

@test "Test authorization info" {
  cd sources/auth

  dork-compose info | grep 'password protected'
}


@test "Test authorization login" {
  cd sources/auth

  dork-compose up -d

  # Test if the containers started
  docker ps | grep 'auth_http_1'
  docker ps | grep 'auth_web_1'

  # Test if auth files are installed.
  ls -la ~/.dork/auth | grep auth.dork
  ls -la ~/.dork/auth | grep web--auth.dork

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the containers are accessible using no login.
  curl --resolve auth.dork:80:127.0.0.1 http://auth.dork | grep '<h1>Testpage.</h1>'
  curl -I --resolve web--auth.dork:80:127.0.0.1 http://web--auth.dork | grep '401 Unauthorized'

  # Test if the container is accessible using a login.
  curl -u dork:dork --resolve web--auth.dork:80:127.0.0.1 http://web--auth.dork | grep '<h1>Testpage.</h1>'

  dork-compose down -v --rmi local

  # Test if the services has been removed.
  ! docker ps -a | grep 'auth_http_1'
  ! docker ps -a | grep 'auth_web_1'

  # Test if auth files have been removed.
  ! ls -la ~/.dork/auth | grep auth.dork
  ! ls -la ~/.dork/auth | grep web--auth.dork
}

@test "Test authorization override for a service" {
  cd sources/auth/switched

  dork-compose up -d

  # Test if the containers started
  docker ps | grep 'switched_http_1'
  docker ps | grep 'switched_web_1'

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the containers are accessible using no login.
  curl --resolve web--switched.dork:80:127.0.0.1 http://web--switched.dork | grep '<h1>Testpage.</h1>'
  curl -I --resolve switched.dork:80:127.0.0.1 http://switched.dork | grep '401 Unauthorized'

  # Test if the container is accessible using a login.
  curl -u dork:dork --resolve switched.dork:80:127.0.0.1 http://switched.dork | grep '<h1>Testpage.</h1>'

  dork-compose down -v --rmi local

  # Test if the services has been removed.
  ! docker ps -a | grep 'switched_http_1'
  ! docker ps -a | grep 'switched_web_1'
}
