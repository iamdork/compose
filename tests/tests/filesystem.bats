#!/usr/bin/env bats

load common

@test "Create and remove snapshot" {
  cd sources/filesystem
  dork-compose up -d

  dork-compose exec web sh -c "echo \"Test\" > /usr/share/nginx/html/index.html"
  dork-compose snapshot save test
  ls -la ~/.dork/snapshots/filesystem | grep test
  dork-compose snapshot rm test

  ! ls -la ~/.dork/snapshots/filesystem | grep test
}

@test "Load a snapshot" {
  cd sources/filesystem
  dork-compose up -d
  dork-compose exec web sh -c "echo \"Test\" > /usr/share/nginx/html/index.html"
  get filesystem.dork | grep "Test"

  dork-compose snapshot save test
  sleep 1

  dork-compose exec web sh -c "echo \"Another Test\" > /usr/share/nginx/html/index.html"
  get filesystem.dork | grep "Another Test"

  sudo dork-compose snapshot load test
  sleep 1

  get filesystem.dork | grep "Test"

  dork-compose snapshot rm test
}
