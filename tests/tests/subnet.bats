#!/usr/bin/env bats

load common

get_subnet() {
  echo $(docker network inspect "$1" \
    | python -c 'import json,sys;obj=json.load(sys.stdin);print obj[0]["IPAM"]["Config"][0]["Subnet"];')
}


@test "Test setting a certain subnet" {
  export DORK_PLUGINS="env:multi:lib:proxy:dns:subnet"
  export DORK_SUBNET_DEFAULT="10.0.0.0/24"
  cd $SOURCES/simple

  dork-compose up -d

  network=$(get_subnet "simple_default")

  # This is the first network which was created, therefore the network should
  # match the default subnet.
  [ "$network" == "$DORK_SUBNET_DEFAULT" ]

  dork-compose down -v --rmi local

}

@test "Test creating several projects with a managed subnet" {
  export DORK_PLUGINS="env:multi:lib:proxy:dns:subnet"
  export DORK_SUBNET_DEFAULT="192.168.1.0/28"
  cd $SOURCES/multi/one && dork-compose up -d
  cd $SOURCES/multi/two && dork-compose up -d
  cd $SOURCES/multi/three && dork-compose up -d

  # Check if the first network is correct.
  network1=$(get_subnet "one_default")
  [ "$network1" == "192.168.1.0/28" ]

  # Check if the second network is correct.
  network2=$(get_subnet "two_default")
  [ "$network2" == "192.168.1.16/28" ]

  # Check if the third network is correct.
  network3=$(get_subnet "three_default")
  [ "$network3" == "192.168.1.32/28" ]

  cd $SOURCES/multi/one && dork-compose down -v --rmi local
  cd $SOURCES/multi/two && dork-compose down -v --rmi local
  cd $SOURCES/multi/three && dork-compose down -v --rmi local
}

@test "Test creating a project with managed subnet besides existing project" {
  # Up a project without the subnet plugin
  export DORK_PLUGINS="env:multi:lib:proxy:dns"
  cd $SOURCES/multi/one && dork-compose up -d

  # Up a project with the subnet plugin.
  export DORK_PLUGINS="env:multi:lib:proxy:dns:subnet"
  export DORK_SUBNET_DEFAULT="10.0.0.0/24"
  cd $SOURCES/multi/two && dork-compose up -d

  # Check if the first network is correct.
  network=$(get_subnet "two_default")
  [ "$network" == "$DORK_SUBNET_DEFAULT" ]

  cd $SOURCES/multi/one && dork-compose down -v --rmi local
  cd $SOURCES/multi/two && dork-compose down -v --rmi local
}