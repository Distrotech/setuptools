#!/bin/sh
export VERSION="0.6.6"

# tagging
hg tag $VERSION
hg ci -m "bumped revision"

# creating the 3k script
mkdir ./temp
cp distribute_setup.py ./temp/distribute_setup.py
cd ./temp
2to3 -w distribute_setup.py > /dev/null
mv distribute_setup.py ../distribute_setup_3k.py
cd ..
rm -rf ./temp

# creating the releases
rm -rf ./dist

# now preparing the source release, pushing it and its doc
python2.6 setup.py -q egg_info -RDb '' sdist register upload
python2.6 setup.py build_sphinx upload_docs

# pushing the bootstrap scripts
scp distribute_setup.py ziade.org:nightly/build/
scp distribute_setup_3k.py ziade.org:nightly/build/

# starting the new dev

