# CMAKE generated file: DO NOT EDIT!
# Generated by "Unix Makefiles" Generator, CMake Version 3.10

# Delete rule output on recipe failure.
.DELETE_ON_ERROR:


#=============================================================================
# Special targets provided by cmake.

# Disable implicit rules so canonical targets will work.
.SUFFIXES:


# Remove some rules from gmake that .SUFFIXES does not remove.
SUFFIXES =

.SUFFIXES: .hpux_make_needs_suffix_list


# Suppress display of executed commands.
$(VERBOSE).SILENT:


# A target that is always out of date.
cmake_force:

.PHONY : cmake_force

#=============================================================================
# Set environment variables for the build.

# The shell in which to execute make rules.
SHELL = /bin/sh

# The CMake executable.
CMAKE_COMMAND = /usr/bin/cmake

# The command to remove a file.
RM = /usr/bin/cmake -E remove -f

# Escaping for special characters.
EQUALS = =

# The top-level source directory on which CMake was run.
CMAKE_SOURCE_DIR = /home/gulsum/galaxy/tools/racon

# The top-level build directory on which CMake was run.
CMAKE_BINARY_DIR = /home/gulsum/galaxy/tools/racon

# Include any dependencies generated for this target.
include vendor/spoa/CMakeFiles/spoa.dir/depend.make

# Include the progress variables for this target.
include vendor/spoa/CMakeFiles/spoa.dir/progress.make

# Include the compile flags for this target's objects.
include vendor/spoa/CMakeFiles/spoa.dir/flags.make

vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o: vendor/spoa/CMakeFiles/spoa.dir/flags.make
vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o: vendor/spoa/src/alignment_engine.cpp
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/home/gulsum/galaxy/tools/racon/CMakeFiles --progress-num=$(CMAKE_PROGRESS_1) "Building CXX object vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++  $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/spoa.dir/src/alignment_engine.cpp.o -c /home/gulsum/galaxy/tools/racon/vendor/spoa/src/alignment_engine.cpp

vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/spoa.dir/src/alignment_engine.cpp.i"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /home/gulsum/galaxy/tools/racon/vendor/spoa/src/alignment_engine.cpp > CMakeFiles/spoa.dir/src/alignment_engine.cpp.i

vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/spoa.dir/src/alignment_engine.cpp.s"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /home/gulsum/galaxy/tools/racon/vendor/spoa/src/alignment_engine.cpp -o CMakeFiles/spoa.dir/src/alignment_engine.cpp.s

vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o.requires:

.PHONY : vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o.requires

vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o.provides: vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o.requires
	$(MAKE) -f vendor/spoa/CMakeFiles/spoa.dir/build.make vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o.provides.build
.PHONY : vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o.provides

vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o.provides.build: vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o


vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o: vendor/spoa/CMakeFiles/spoa.dir/flags.make
vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o: vendor/spoa/src/graph.cpp
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/home/gulsum/galaxy/tools/racon/CMakeFiles --progress-num=$(CMAKE_PROGRESS_2) "Building CXX object vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++  $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/spoa.dir/src/graph.cpp.o -c /home/gulsum/galaxy/tools/racon/vendor/spoa/src/graph.cpp

vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/spoa.dir/src/graph.cpp.i"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /home/gulsum/galaxy/tools/racon/vendor/spoa/src/graph.cpp > CMakeFiles/spoa.dir/src/graph.cpp.i

vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/spoa.dir/src/graph.cpp.s"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /home/gulsum/galaxy/tools/racon/vendor/spoa/src/graph.cpp -o CMakeFiles/spoa.dir/src/graph.cpp.s

vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o.requires:

.PHONY : vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o.requires

vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o.provides: vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o.requires
	$(MAKE) -f vendor/spoa/CMakeFiles/spoa.dir/build.make vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o.provides.build
.PHONY : vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o.provides

vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o.provides.build: vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o


vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o: vendor/spoa/CMakeFiles/spoa.dir/flags.make
vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o: vendor/spoa/src/simd_alignment_engine.cpp
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/home/gulsum/galaxy/tools/racon/CMakeFiles --progress-num=$(CMAKE_PROGRESS_3) "Building CXX object vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++  $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o -c /home/gulsum/galaxy/tools/racon/vendor/spoa/src/simd_alignment_engine.cpp

vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.i"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /home/gulsum/galaxy/tools/racon/vendor/spoa/src/simd_alignment_engine.cpp > CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.i

vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.s"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /home/gulsum/galaxy/tools/racon/vendor/spoa/src/simd_alignment_engine.cpp -o CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.s

vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o.requires:

.PHONY : vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o.requires

vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o.provides: vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o.requires
	$(MAKE) -f vendor/spoa/CMakeFiles/spoa.dir/build.make vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o.provides.build
.PHONY : vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o.provides

vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o.provides.build: vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o


vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o: vendor/spoa/CMakeFiles/spoa.dir/flags.make
vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o: vendor/spoa/src/sisd_alignment_engine.cpp
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --progress-dir=/home/gulsum/galaxy/tools/racon/CMakeFiles --progress-num=$(CMAKE_PROGRESS_4) "Building CXX object vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++  $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -o CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o -c /home/gulsum/galaxy/tools/racon/vendor/spoa/src/sisd_alignment_engine.cpp

vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.i: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Preprocessing CXX source to CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.i"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -E /home/gulsum/galaxy/tools/racon/vendor/spoa/src/sisd_alignment_engine.cpp > CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.i

vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.s: cmake_force
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green "Compiling CXX source to assembly CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.s"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && /usr/bin/c++ $(CXX_DEFINES) $(CXX_INCLUDES) $(CXX_FLAGS) -S /home/gulsum/galaxy/tools/racon/vendor/spoa/src/sisd_alignment_engine.cpp -o CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.s

vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o.requires:

.PHONY : vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o.requires

vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o.provides: vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o.requires
	$(MAKE) -f vendor/spoa/CMakeFiles/spoa.dir/build.make vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o.provides.build
.PHONY : vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o.provides

vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o.provides.build: vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o


# Object files for target spoa
spoa_OBJECTS = \
"CMakeFiles/spoa.dir/src/alignment_engine.cpp.o" \
"CMakeFiles/spoa.dir/src/graph.cpp.o" \
"CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o" \
"CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o"

# External object files for target spoa
spoa_EXTERNAL_OBJECTS =

vendor/spoa/lib/libspoa.a: vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o
vendor/spoa/lib/libspoa.a: vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o
vendor/spoa/lib/libspoa.a: vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o
vendor/spoa/lib/libspoa.a: vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o
vendor/spoa/lib/libspoa.a: vendor/spoa/CMakeFiles/spoa.dir/build.make
vendor/spoa/lib/libspoa.a: vendor/spoa/CMakeFiles/spoa.dir/link.txt
	@$(CMAKE_COMMAND) -E cmake_echo_color --switch=$(COLOR) --green --bold --progress-dir=/home/gulsum/galaxy/tools/racon/CMakeFiles --progress-num=$(CMAKE_PROGRESS_5) "Linking CXX static library lib/libspoa.a"
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && $(CMAKE_COMMAND) -P CMakeFiles/spoa.dir/cmake_clean_target.cmake
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && $(CMAKE_COMMAND) -E cmake_link_script CMakeFiles/spoa.dir/link.txt --verbose=$(VERBOSE)

# Rule to build all files generated by this target.
vendor/spoa/CMakeFiles/spoa.dir/build: vendor/spoa/lib/libspoa.a

.PHONY : vendor/spoa/CMakeFiles/spoa.dir/build

vendor/spoa/CMakeFiles/spoa.dir/requires: vendor/spoa/CMakeFiles/spoa.dir/src/alignment_engine.cpp.o.requires
vendor/spoa/CMakeFiles/spoa.dir/requires: vendor/spoa/CMakeFiles/spoa.dir/src/graph.cpp.o.requires
vendor/spoa/CMakeFiles/spoa.dir/requires: vendor/spoa/CMakeFiles/spoa.dir/src/simd_alignment_engine.cpp.o.requires
vendor/spoa/CMakeFiles/spoa.dir/requires: vendor/spoa/CMakeFiles/spoa.dir/src/sisd_alignment_engine.cpp.o.requires

.PHONY : vendor/spoa/CMakeFiles/spoa.dir/requires

vendor/spoa/CMakeFiles/spoa.dir/clean:
	cd /home/gulsum/galaxy/tools/racon/vendor/spoa && $(CMAKE_COMMAND) -P CMakeFiles/spoa.dir/cmake_clean.cmake
.PHONY : vendor/spoa/CMakeFiles/spoa.dir/clean

vendor/spoa/CMakeFiles/spoa.dir/depend:
	cd /home/gulsum/galaxy/tools/racon && $(CMAKE_COMMAND) -E cmake_depends "Unix Makefiles" /home/gulsum/galaxy/tools/racon /home/gulsum/galaxy/tools/racon/vendor/spoa /home/gulsum/galaxy/tools/racon /home/gulsum/galaxy/tools/racon/vendor/spoa /home/gulsum/galaxy/tools/racon/vendor/spoa/CMakeFiles/spoa.dir/DependInfo.cmake --color=$(COLOR)
.PHONY : vendor/spoa/CMakeFiles/spoa.dir/depend

