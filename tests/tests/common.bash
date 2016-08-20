#!/usr/bin/env bash

export SOURCES="$(pwd)/sources"
export DORK_LIBRARY_PATH="$(pwd)/lib"

get() {
  curl --resolve $1:80:127.0.0.1 http://$1/$2
}
