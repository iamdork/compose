#!/usr/bin/env bats

load common

@test "Test backsyncing of build results." {
  cd sources/buildresults
  dork-compose up -d
  cat html/test.txt | grep "This is created during build."
  cat test/test.txt | grep "This is also created during build."
  rm -rf html
  rm -rf test
  dork-compose down --rmi all
}
