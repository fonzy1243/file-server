cmake_minimum_required(VERSION 3.28)

project(file-server)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED true)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_definitions(-DASIO_STANDALONE -D_WIN32_WINNT=0x0601)

include_directories(${CMAKE_SOURCE_DIR}/include)

add_executable(client src/client/client.cpp)
add_executable(server src/server/server.cpp)
