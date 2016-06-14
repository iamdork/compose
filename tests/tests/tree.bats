#!/usr/bin/env bats

load common

@test "Test tree setup" {
  cd $SOURCES/tree/a
  dork-compose up -d
  cd $SOURCES/tree/b
  dork-compose up -d

  # Sleep to wait for the container to boot.
  sleep 1

  # Test if the container is accessible.
  get tree--a.dork | grep '<h1>Testpage A</h1>'

  # Test if the container is accessible.
  get tree--b.dork | grep '<h1>Testpage B</h1>'

  cd $SOURCES/tree/a
  dork-compose down
  cd $SOURCES/tree/b
  dork-compose down
}