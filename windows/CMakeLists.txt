# Windows build of FH2 Recompiled on the ShiftGlue SDK (arcanite24/shiftglue-sdk, the SDK
# of Pinyon Shift / Forza Horizon 1) with its Vulkan FH1 renderer (GPU plugin "fh1").
#
# Derived from upstream's evaluation prototype (branch comparacao/shiftglue,
# prototipos/fh2-shiftglue), which rendered FH2 correctly on PC with correct car/wall
# collisions. The codegen inputs (manifest overrides) and the FH2 fixes are shared with
# the Linux/Android tree in ../app, so upstream improvements to them reach this build.
# See README.md in this folder.
cmake_minimum_required(VERSION 3.25)
project(fh2 LANGUAGES C CXX)
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(WIN32)
    # As in Pinyon Shift: SDL's optional libusb HID backend is not available on Windows.
    set(SDL_HIDAPI_LIBUSB OFF CACHE BOOL "Disable optional libusb HID backend on Windows" FORCE)
endif()
include(rexglue_proto.cmake)

set(FH2_APP_SRC ${CMAKE_CURRENT_SOURCE_DIR}/../app/src)
set(FH2_SOURCES
    src/main.cpp
    src/fh2_toque.cpp
    src/fh2_medidor.cpp
    src/fh2_wheel_gear.cpp
    src/fh2_reverse_guard.cpp
    src/fh2_telemetry.cpp
    ${FH2_APP_SRC}/fh2_teste_entrada.cpp
    ${FH2_APP_SRC}/fh2_captura.cpp
    ${FH2_APP_SRC}/fh2_correcoes.cpp)
if(WIN32)
    add_executable(fh2 WIN32 ${FH2_SOURCES})
    target_link_libraries(fh2 PRIVATE ws2_32)   # fh2_telemetry.cpp: UDP to 127.0.0.1
else()
    add_executable(fh2 ${FH2_SOURCES})
endif()
target_include_directories(fh2 PRIVATE ${FH2_APP_SRC})
rexglue_setup_target(fh2 GPU_PLUGINS fh1)
if(TARGET imgui)
    target_include_directories(fh2 PRIVATE $<TARGET_PROPERTY:imgui,INTERFACE_INCLUDE_DIRECTORIES>)
endif()
if(TARGET renderdoc)
    target_include_directories(fh2 PRIVATE $<TARGET_PROPERTY:renderdoc,INTERFACE_INCLUDE_DIRECTORIES>)
endif()
