# User C module wiring the NNoM keyword-spotting model into MicroPython
# as the `speech_commands` module.
#
# NNOM_DIR must point at a checkout of https://github.com/majianjia/nnom
# (build.sh clones the pinned revision and sets it).

if(NOT DEFINED NNOM_DIR)
    set(NNOM_DIR ${CMAKE_CURRENT_LIST_DIR}/../../build/nnom)
endif()

add_library(usermod_speech_commands INTERFACE)

file(GLOB NNOM_SRC
    ${NNOM_DIR}/src/backends/*.c
    ${NNOM_DIR}/src/core/*.c
    ${NNOM_DIR}/src/layers/*.c
)

set(SPEECH_COMMANDS_SRC
    ${CMAKE_CURRENT_LIST_DIR}/nnom_module.c
    ${CMAKE_CURRENT_LIST_DIR}/kws.c
    ${NNOM_DIR}/examples/keyword_spotting/mfcc.c
    ${NNOM_SRC}
)

target_sources(usermod_speech_commands INTERFACE ${SPEECH_COMMANDS_SRC})

# Compile the recognition code (MFCC + NNoM inference) at maximum
# optimization. Applied per-source so -Ofast/-ffast-math cannot leak into
# the MicroPython core, where it would break float/NaN semantics.
set_source_files_properties(${SPEECH_COMMANDS_SRC}
    PROPERTIES COMPILE_OPTIONS "-Ofast;-funroll-loops;-w")

# This module's directory comes first so its weights.h and nnom_port.h win
# over same-named files in the NNoM example directory.
target_include_directories(usermod_speech_commands INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}
    ${NNOM_DIR}/inc
    ${NNOM_DIR}/examples/keyword_spotting
)

target_link_libraries(usermod INTERFACE usermod_speech_commands)
