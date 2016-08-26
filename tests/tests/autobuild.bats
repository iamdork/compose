#!/usr/bin/env bash

load common

@test "Test autobuild with subpaths" {
  cd sources/autobuild

  dork-compose up -d --build

  sleep 1
  # Test if the container is accessible.
  get a--autobuild.dork | grep '<h1>I am autobuild!</h1>'
  get b--autobuild.dork | grep '<h2>Autobuild subfolder.</h2>'

  dork-compose down
}