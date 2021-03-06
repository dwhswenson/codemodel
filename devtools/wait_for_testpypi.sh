#!/bin/bash

SETUP_PY=$1

VERSION=`python $SETUP_PY --version`
PROJECT=`python $SETUP_PY --name`

echo "Searching test.pypi for  $VERSION"

MISSING_VERSION=true
while $MISSING_VERSION; do
    pip_results=`pip search -i https://test.pypi.org/pypi $PROJECT`
    pip search -i https://test.pypi.org/pypi $PROJECT
    #echo $pip_results
    grepped=`echo $pip_results | grep $PROJECT`
    #echo "Grepped:" $grepped
    if [ -n "$grepped" ]; then
        MISSING_VERSION=false
    else
        echo "Waiting 5 seconds for the version to register"
        sleep 5
    fi
done
