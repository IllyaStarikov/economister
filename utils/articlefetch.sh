#!/bin/bash

papeer list https://www.economist.com/weeklyedition/ -o json --selector='h3>a' > ./temp/articlelist.json