cmake_minimum_required(VERSION 3.2)
project(thread_pool)

include(GNUInstallDirs)

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${PROJECT_BINARY_DIR}/bin)

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -pedantic -march=native")
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(THREADS_PREFER_PTHREAD_FLAG ON)

find_package(Threads REQUIRED)

option(thread_pool_build_tests "Build thread_pool unit tests" OFF)

add_library(thread_pool STATIC
    src/thread_pool.cpp)

target_link_libraries(thread_pool Threads::Threads)

target_include_directories(thread_pool PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>)

install(TARGETS thread_pool DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/include/thread_pool DESTINATION ${CMAKE_INSTALL_INCLUDEDIR})

if (thread_pool_build_tests)
    add_executable(thread_pool_test test/thread_pool_test.cpp)

    if (NOT TARGET gtest_main)
        add_subdirectory(vendor/googletest/googletest EXCLUDE_FROM_ALL)
    endif()

    target_link_libraries(thread_pool_test thread_pool gtest_main)
endif()
