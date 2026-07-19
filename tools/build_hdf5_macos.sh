#!/bin/bash
set -eux

export MACOSX_DEPLOYMENT_TARGET=11.0

CMAKE_ARCH=""
if [[ "${ARCHFLAGS:-}" == *"arm64"* ]]; then
    CMAKE_ARCH="arm64"
elif [[ "${ARCHFLAGS:-}" == *"x86_64"* ]]; then
    CMAKE_ARCH="x86_64"
fi

HDF5_VER=2.1.1

curl -L \
https://github.com/HDFGroup/hdf5/releases/download/${HDF5_VER}/hdf5.tar.gz \
-o hdf5.tar.gz

tar xf hdf5.tar.gz
cd hdf5-${HDF5_VER}

rm -rf build

if command -v nproc &> /dev/null; then
    CORES=$(nproc)
elif command -v sysctl &> /dev/null; then
    CORES=$(sysctl -n hw.ncpu)
else
    CORES=2
fi

cmake \
-B build \
${CMAKE_ARCH:+-DCMAKE_OSX_ARCHITECTURES=$CMAKE_ARCH} \
-DCMAKE_BUILD_TYPE=Release \
-DCMAKE_INSTALL_PREFIX=/tmp/hdf5 \
-DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
-DBUILD_SHARED_LIBS=ON \
-DHDF5_BUILD_CPP_LIB=OFF \
-DHDF5_BUILD_TOOLS=OFF \
-DHDF5_BUILD_EXAMPLES=OFF

cmake --build build --parallel "$CORES"
cmake --install build
