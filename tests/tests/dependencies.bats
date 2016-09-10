#!/usr/bin/env bats

load common

@test "Test backsyncing of build dependencies." {
  cd sources/dependencies
  dork-compose up -d
  cat html/test.txt | grep "This is created during build."
  cat test/test.txt | grep "This is also created during build."
  dork-compose down --rmi all
}
