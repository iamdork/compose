#!/usr/bin/env bats

SOURCES="$(pwd)/sources"
export DORK_LIBRARY_PATH="$(pwd)/lib"


@test "Start multiple projects" {
  cd $SOURCES/multi/one && dork-compose up -d
  cd $SOURCES/multi/two && dork-compose up -d
  cd $SOURCES/multi/three && dork-compose up -d

  # Test if the http services aree available and running.
  docker ps | grep 'one_http_1'
  docker ps | grep 'two_http_1'
  docker ps | grep 'three_http_1'

  # Sleep to wait for the containers to boot.
  sleep 1

  # Test if the container is accessible.
  curl http://one.127.0.0.1.xip.io | grep '<h1>Testpage 1.</h1>'
  curl http://two.127.0.0.1.xip.io | grep '<h1>Testpage 2.</h1>'
  curl http://three.127.0.0.1.xip.io | grep '<h1>Testpage 3.</h1>'

  cd $SOURCES/multi/one && dork-compose down
  cd $SOURCES/multi/two && dork-compose down
  cd $SOURCES/multi/three && dork-compose down

  # Test if the http service has been removed.
  ! docker ps -a | grep 'one_http_1'
  ! docker ps -a | grep 'two_http_1'
  ! docker ps -a | grep 'three_http_1'
}


@test "Start multiple projects simultaneously" {
  (cd $SOURCES/multi/one; dork-compose up -d) &
  (cd $SOURCES/multi/two && dork-compose up -d) &
  (cd $SOURCES/multi/three && dork-compose up -d) &
  wait

  # Test if the http services aree available and running.
  docker ps | grep 'one_http_1'
  docker ps | grep 'two_http_1'
  docker ps | grep 'three_http_1'

  # Sleep to wait for the containers to boot.
  sleep 1

  # Test if the container is accessible.
  curl http://one.127.0.0.1.xip.io | grep '<h1>Testpage 1.</h1>'
  curl http://two.127.0.0.1.xip.io | grep '<h1>Testpage 2.</h1>'
  curl http://three.127.0.0.1.xip.io | grep '<h1>Testpage 3.</h1>'

  (cd $SOURCES/multi/one && dork-compose down) &
  (cd $SOURCES/multi/two && dork-compose down) &
  (cd $SOURCES/multi/three && dork-compose down) &
  wait

  # Test if the http service has been removed.
  ! docker ps -a | grep 'one_http_1'
  ! docker ps -a | grep 'two_http_1'
  ! docker ps -a | grep 'three_http_1'
}
