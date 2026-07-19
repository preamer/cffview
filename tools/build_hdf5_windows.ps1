$ErrorActionPreference = "Stop"

$ver="2.1.1"
$installDir = "$env:USERPROFILE\hdf5"

Invoke-WebRequest `
  "https://github.com/HDFGroup/hdf5/releases/download/$ver/hdf5.zip" `
  -OutFile hdf5.zip

New-Item -ItemType Directory -Force -Path ".\hdf5_src"
Expand-Archive hdf5.zip -DestinationPath ".\hdf5_src"

cd ".\hdf5_src\hdf5-$ver"

cmake `
  -B build `
  -G "Ninja" `
  -DCMAKE_BUILD_TYPE=Release `
  -DCMAKE_INSTALL_PREFIX="$installDir" `
  -DBUILD_SHARED_LIBS=ON `
  -DHDF5_BUILD_CPP_LIB=OFF `
  -DHDF5_BUILD_TOOLS=OFF `
  -DHDF5_BUILD_EXAMPLES=OFF

cmake --build build
cmake --install build

Write-Host "HDF5 successfully installed to: $installDir"
