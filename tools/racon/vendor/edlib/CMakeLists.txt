cmake_minimum_required(VERSION 3.2 FATAL_ERROR)
project(edlib)

set(MACOSX (${CMAKE_SYSTEM_NAME} MATCHES "Darwin"))

if(CMAKE_BUILD_TYPE MATCHES Debug)
  message("Debug mode")
endif()

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)  # Falling back to different standard it not allowed.
set(CMAKE_CXX_EXTENSIONS NO)  # Make sure no compiler-specific features are used.

# Set strict warnings.
if(MSVC)
  # Force to always compile with W4
  if(CMAKE_CXX_FLAGS MATCHES "/W[0-4]")
    string(REGEX REPLACE "/W[0-4]" "/W4" CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS}")
  else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /W4")
  endif()
else()
  message("Setting warning flags")
  set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -pedantic")
endif()

# Define output directories for created binaries and libraries.
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

file(GLOB SOURCES "edlib/src/*.cpp")

# Create libraries.
add_library(edlib SHARED ${SOURCES})

target_include_directories(edlib PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/edlib/include>
    $<INSTALL_INTERFACE:include>)

add_library(edlib_static STATIC ${SOURCES})

target_include_directories(edlib_static PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/edlib/include>
    $<INSTALL_INTERFACE:include>)

# Build binaries.
add_executable(helloWorld apps/hello-world/helloWorld.c)
target_link_libraries(helloWorld edlib_static)

add_executable(runTests test/runTests.cpp)
target_link_libraries(runTests edlib_static)

if (NOT WIN32) # If on windows, do not build binaries that do not support windows.
  add_executable(edlib-aligner apps/aligner/aligner.cpp)
  target_link_libraries(edlib-aligner edlib_static)
endif()


# Create target 'install' for installing libraries.
install(TARGETS edlib edlib_static DESTINATION lib)
install(FILES edlib/include/edlib.h DESTINATION include)
