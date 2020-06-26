#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "cudapoa" for configuration "Release"
set_property(TARGET cudapoa APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(cudapoa PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libcudapoa.a"
  )

list(APPEND _IMPORT_CHECK_TARGETS cudapoa )
list(APPEND _IMPORT_CHECK_FILES_FOR_cudapoa "${_IMPORT_PREFIX}/lib/libcudapoa.a" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
