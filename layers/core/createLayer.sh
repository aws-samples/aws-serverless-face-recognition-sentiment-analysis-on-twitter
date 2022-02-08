#!/bin/bash

read CURDIR <<< $(pwd)
DIRNAME=$(echo "${PWD##*/}")
docker build --tag layer:latest .
docker run --rm -v ${CURDIR}:/dest layer:latest cp code.zip /dest/${DIRNAME}.zip