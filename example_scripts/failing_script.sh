#!/usr/bin/env bash

set -e
touch /tmp/foo.txt

mkdir /tmp/never/gonna/happen/  # This fails because it's not called with -p to create the intermediate directories.

echo "I ran successfully"

