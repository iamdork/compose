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
  curl -I --resolve auth.dork:80:127.0.0.1 http://auth.dork | grep '401 Unauthorized'
  curl -I --resolve web--auth.dork:80:127.0.0.1 http://web--auth.dork | grep '401 Unauthorized'

  # Test if the container is accessible using a login.
  curl -u dork:dork --resolve auth.dork:80:127.0.0.1 http://auth.dork | grep '<h1>Testpage.</h1>'
  curl -u dork:dork --resolve web--auth.dork:80:127.0.0.1 http://web--auth.dork | grep '<h1>Testpage.</h1>'

  dork-compose down -v --rmi local

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
  curl -u dork:dork --resolve noauth.dork:80:127.0.0.1 http://noauth.dork | grep '<h1>Testpage.</h1>'

  # The web container should be accessible with a login.
  curl -u dork:dork --resolve web--noauth.dork:80:127.0.0.1 http://web--noauth.dork | grep '<h1>Testpage.</h1>'

  dork-compose down -v --rmi local

  # Test if the services has been removed.
  ! docker ps -a | grep 'noauth_http_1'
  ! docker ps -a | grep 'noauth_web_1'
}
