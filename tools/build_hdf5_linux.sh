#!/bin/bash
set -eux

yum install -y cmake gcc-c++ make

HDF5_VER=2.1.1

curl -L \
https://github.com/HDFGroup/hdf5/releases/download/${HDF5_VER}/hdf5.tar.gz \
-o hdf5.tar.gz

tar xf hdf5.tar.gz
cd hdf5-${HDF5_VER}

mkdir -p /opt/hdf5

cmake \
-B build \
-DCMAKE_BUILD_TYPE=Release \
-DCMAKE_INSTALL_PREFIX=/opt/hdf5 \
-DBUILD_SHARED_LIBS=ON \
-DHDF5_BUILD_CPP_LIB=OFF \
-DHDF5_BUILD_TOOLS=OFF \
-DHDF5_BUILD_EXAMPLES=OFF

cmake --build build -j4
cmake --install build
