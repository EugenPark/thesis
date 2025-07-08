#!/bin/bash

# If the linked libraries are outdated and need to be recopied copy libresolv_wrapper.so into /cockroach/artifacts directory

set -e

image_tag="cockroach-builder"

docker build \
	-t $image_tag \
	.

docker run --rm -it -v ./../../:/app --workdir=/app/cockroach  -v bzlhome:/home/roach:delegated -u 1000:1000 $image_tag

