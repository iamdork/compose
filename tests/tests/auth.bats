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

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the containers are accessible using no login.
  curl -I http://auth.dork.io | grep '401 Unauthorized'
  curl -I http://web--auth.dork.io | grep '401 Unauthorized'

  # Test if the container is accessible using a login.
  curl -u dork:dork http://auth.dork.io | grep '<h1>Testpage.</h1>'
  curl -u dork:dork http://web--auth.dork.io | grep '<h1>Testpage.</h1>'

  dork-compose down

  # Test if the services has been removed.
  ! docker ps -a | grep 'auth_http_1'
  ! docker ps -a | grep 'auth_web_1'
}

@test "Test authorization override for a service" {
  cd sources/auth/noauth

  dork-compose up -d

  # Test if the containers started
  docker ps | grep 'noauth_http_1'
  docker ps | grep 'noauth_web_1'

  # Sleep to wait for the container to boot.
  sleep 1

  # The main http container should be accessible using the login
  curl -u dork:dork http://noauth.dork.io | grep '<h1>Testpage.</h1>'

  # The web container should be accessible with a login.
  curl -u dork:dork http://web--noauth.dork.io | grep '<h1>Testpage.</h1>'

  dork-compose down

  # Test if the services has been removed.
  ! docker ps -a | grep 'noauth_http_1'
  ! docker ps -a | grep 'noauth_web_1'
}
