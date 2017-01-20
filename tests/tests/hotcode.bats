#!/usr/bin/env bats

load common

@test "Test for hot code changes." {
  cd sources/hotcode

  dork-compose up -d

  # Test if the http service is available and running.
  docker ps | grep 'hotcode_a_1'

  # Sleep to wait for the container to boot.
  sleep 1

  get a--hotcode.dork | grep 'This is a test.'
  rm html/index.html && echo "This is a hotcode test." >> html/index.html
  get a--hotcode.dork | grep 'This is a hotcode test.'
  rm html/index.html && echo "This is a test." >> html/index.html

  dork-compose down -v --rmi local

  # Test if the http service has been removed.
  ! docker ps -a | grep 'hotcode_a_1'
}

@test "Test hotcode environment override." {
  cd sources/hotcode

  dork-compose up -d

  # Test if the http service is available and running.
  docker ps | grep 'hotcode_b_1'

  # Sleep to wait for the container to boot.
  sleep 1

  get b--hotcode.dork | grep 'This is a test.'
  rm html/index.html && echo "This is a hotcode test." >> html/index.html
  get b--hotcode.dork | grep 'This is a test.'
  rm html/index.html && echo "This is a test." >> html/index.html

  dork-compose down -v --rmi local

  # Test if the http service has been removed.
  ! docker ps -a | grep 'hotcode_b_1'
}
