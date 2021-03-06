#!/usr/bin/env bash

export SOURCES="$(pwd)/sources"
export DORK_LIBRARY_PATH="$(pwd)/lib"
export DORK_PROXY_HTTPS_SIGNING="none"
export DORK_PLUGINS='env:multi:lib:autobuild:hotcode:git:filesystem:proxy:dns:vault'

get() {
  curl --resolve $1:80:127.0.0.1 http://$1/$2
}
