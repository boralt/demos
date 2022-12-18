# scala demo

Team hiking simulation Program

## Credits
This utility uses yaml-cpp parsing library. It is copied into source tree under yaml-cpp folder

## Pre-requisites
- cmake version 3.16 or later
- C++14 capable compiler 
- Internet connection. This project will download googletest sources.

## build
cmake -B build .  
cmake --build build  

## run
./build/scala_demo scenario1.yaml 

## run unit tests
./build/scala_test

## assumptions
The main travelers group is defined. Additional travelers assisted on the crossings 
are not automatically joining main traveling group.

## config file format


```
base-group:
  - speed: 100
  - speed: 50
crossings:
  - length: 250
    group:
      - speed: 2.5
  - length: 150
    group:
      - speed: 25
      - speed: 15
```


