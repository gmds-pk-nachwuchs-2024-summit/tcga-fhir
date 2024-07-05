#!/bin/bash

for bundle in ./bundles/*; do
    echo "$bundle"
    http POST https://fhir.imi.uni-luebeck.de/fhir < $bundle
done