#!/usr/bin/env bash

export SOURCES="$(pwd)/sources"
export DORK_LIBRARY_PATH="$(pwd)/lib"

get() {
  curl http://$1/$2
}
