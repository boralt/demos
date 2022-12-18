cmake_minimum_required(VERSION 3.16)
project(scala_demo)

set(CMAKE_CXX_STANDARD 14)

add_subdirectory(yaml-cpp)

set(SCALA_SOURCES TravelerGroup.h Traveler.h Bridge.h Crossing.h CrossingStrategy.h TwoAtTheTimeCrossingStrategy.cpp TwoAtTheTimeCrossingStrategy.h HikingScenario.cpp HikingScenario.h)

add_executable(scala_demo main.cpp ${SCALA_SOURCES})
add_dependencies(scala_demo yaml-cpp)
message("Searching for ${CMAKE_BINARY_DIR}/yaml-cpp/libyaml-cpp.a")

target_link_libraries(scala_demo LINK_PUBLIC yaml-cpp)
add_dependencies(scala_demo yaml-cpp)
include_directories(${PROJECT_SOURCE_DIR}/yaml-cpp/include)

include(FetchContent)
FetchContent_Declare(
        googletest
        GIT_REPOSITORY https://github.com/google/googletest.git
        GIT_TAG release-1.12.1
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()

add_executable(
        scala_test
        tests/scala_test.cpp
        ${SCALA_SOURCES}
)


target_link_libraries(
        scala_test
        GTest::gtest_main
        yaml-cpp
)


include(GoogleTest)
gtest_discover_tests(scala_test)
