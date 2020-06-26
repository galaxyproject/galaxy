cmake_minimum_required(VERSION 3.2)
project(bioparser)

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/bin)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -pedantic")
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(bioparser_build_tests "Build bioparser unit tests" OFF)

add_library(bioparser INTERFACE)

target_include_directories(bioparser INTERFACE
    ${PROJECT_SOURCE_DIR}/include
    ${PROJECT_SOURCE_DIR}/vendor/zlib
    ${PROJECT_BINARY_DIR}/vendor/zlib)

if (NOT TARGET zlib)
    add_subdirectory(vendor/zlib EXCLUDE_FROM_ALL)
endif()

target_link_libraries(bioparser INTERFACE zlibstatic)

if (bioparser_build_tests)
    set(bioparser_test_data_path ${PROJECT_SOURCE_DIR}/test/data/)
    configure_file(${PROJECT_SOURCE_DIR}/test/bioparser_test_config.h.in
        ${PROJECT_BINARY_DIR}/config/bioparser_test_config.h)
    include_directories(${PROJECT_BINARY_DIR}/config)

    add_executable(bioparser_test test/bioparser_test.cpp)

    if (NOT TARGET gtest_main)
        add_subdirectory(vendor/googletest/googletest EXCLUDE_FROM_ALL)
    endif()

    target_link_libraries(bioparser_test bioparser gtest_main)
endif()
