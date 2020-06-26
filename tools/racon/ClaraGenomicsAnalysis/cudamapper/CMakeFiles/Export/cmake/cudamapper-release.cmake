#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "cudamapper" for configuration "Release"
set_property(TARGET cudamapper APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(cudamapper PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/cudamapper"
  )

list(APPEND _IMPORT_CHECK_TARGETS cudamapper )
list(APPEND _IMPORT_CHECK_FILES_FOR_cudamapper "${_IMPORT_PREFIX}/bin/cudamapper" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
