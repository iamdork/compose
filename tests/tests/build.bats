#!/usr/bin/env bats

load common

@test "Just build the image" {
  cd sources/build
  dork-compose build
  dork-compose down -v --rmi all
}

@test "Test full up." {
  cd sources/build
  dork-compose up --build | grep "This is a test."
  dork-compose down -v --rmi all
}

@test "Test run." {
  cd sources/build
  dork-compose run --rm app | grep "This is a test."
  dork-compose down -v --rmi all
}
