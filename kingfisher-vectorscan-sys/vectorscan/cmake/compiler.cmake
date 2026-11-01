# determine compiler
if (CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    set(CMAKE_COMPILER_IS_CLANG TRUE)
    set(CLANGCXX_MINVER "5")
    message(STATUS "clang++ version ${CMAKE_CXX_COMPILER_VERSION}")
    if (CMAKE_CXX_COMPILER_VERSION VERSION_LESS CLANGCXX_MINVER)
        message(FATAL_ERROR "A minimum of clang++ ${CLANGCXX_MINVER} is required for C++17 support")
    endif()
    string (REGEX REPLACE "^([0-9]+)\\.([0-9]+)\\.([0-9]+)$" "\\1" CLANG_MAJOR_VERSION "${CMAKE_CXX_COMPILER_VERSION}")
endif()

# Keep the Microsoft ABI without pretending cl.exe supports the GNU language
# extensions used throughout the engine. clang-cl uses the Microsoft SDK/STL.
if(MSVC AND NOT CMAKE_COMPILER_IS_CLANG)
    message(FATAL_ERROR "MSVC ABI source builds require LLVM clang-cl, Ninja, and the Visual Studio C++ SDK; configure both CMAKE_C_COMPILER and CMAKE_CXX_COMPILER as clang-cl")
endif()

# compiler version checks TODO: test more compilers
if (CMAKE_COMPILER_IS_GNUCXX)
    set(GNUCXX_MINVER "9")
    message(STATUS "g++ version ${CMAKE_CXX_COMPILER_VERSION}")
    if (CMAKE_CXX_COMPILER_VERSION VERSION_LESS GNUCXX_MINVER)
        message(FATAL_ERROR "A minimum of g++ ${GNUCXX_MINVER} is required for C++17 support")
    endif()
endif()
