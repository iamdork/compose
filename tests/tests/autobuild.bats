#!/usr/bin/env bash

load common

@test "Test simple autobuild" {
  cd sources/autobuild
  export DORK_PLUGINS=env:multi:lib:autobuild:proxy:dns

  dork-compose up -d --build

  sleep 1
  # Test if the container is accessible.
  get a--autobuild.dork | grep '<h1>I am autobuild!</h1>'
  get b--autobuild.dork | grep '<h2>Autobuild subfolder.</h2>'

  dork-compose down
}

@test "Test autobuild .dockerignore" {
  cd sources/autobuild
  export DORK_PLUGINS=env:multi:lib:autobuild:proxy:dns

  dork-compose up -d --build

  sleep 1
  curl --resolve a--autobuild.dork:80:127.0.0.1 http://a--autobuild.dork/sub | grep '404'

  dork-compose down
}

@test "Test autobuild automatic .dockerignore" {
  cd sources/autobuild
  export DORK_PLUGINS=env:multi:lib:autobuild:proxy:dns

  dork-compose up -d --build

  sleep 1
  # Test if the container is accessible.
  curl --resolve a--autobuild.dork:80:127.0.0.1 http://a--autobuild.dork/vendor | grep '404'
  curl --resolve b--autobuild.dork:80:127.0.0.1 http://b--autobuild.dork/vendor | grep '404'

  dork-compose down
}
