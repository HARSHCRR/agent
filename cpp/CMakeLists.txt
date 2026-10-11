cmake_minimum_required(VERSION 3.20)
project(QuantAgentCPP VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compiler optimization and warnings
if(MSVC)
    add_compile_options(/W4)
else()
    add_compile_options(-Wall -Wextra -Wpedantic -O2)
endif()

# Find native libraries
find_package(CURL REQUIRED)
find_package(SQLite3 REQUIRED)

include_directories(
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CURL_INCLUDE_DIRS}
    ${SQLite3_INCLUDE_DIRS}
)

# Main executable
add_executable(quant_agent src/main.cpp)

target_link_libraries(quant_agent PRIVATE
    ${CURL_LIBRARIES}
    ${SQLite3_LIBRARIES}
)
