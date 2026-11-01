/*
 * Copyright (c) 2026, Mick Grove
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *  * Redistributions of source code must retain this copyright notice, this
 *    list of conditions and the following disclaimer.
 *  * Redistributions in binary form must reproduce this copyright notice,
 *    this list of conditions and the following disclaimer in the documentation
 *    and/or other materials provided with the distribution.
 *  * Neither the author's name nor contributor names may be used to endorse
 *    or promote products derived from this software without prior permission.
 *
 * THIS SOFTWARE IS PROVIDED "AS IS", WITHOUT ANY EXPRESS OR IMPLIED WARRANTY,
 * INCLUDING MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE. IN NO EVENT
 * SHALL THE AUTHORS OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES ARISING FROM ITS USE.
 */

#include "gtest/gtest.h"
#include "util/alloc.h"
#include <cstdint>
#include <cstring>

TEST(InternalAlignedAllocator, AllocationAndFreeUseTheSameAllocator) {
    for (size_t alignment : {16u, 64u, 256u}) {
        for (size_t size : {1u, 13u, 4096u}) {
            void *memory = ue2::aligned_malloc_internal(size, alignment);
            ASSERT_NE(nullptr, memory);
            ASSERT_EQ(0u, reinterpret_cast<uintptr_t>(memory) % alignment);
            std::memset(memory, 0xa5, size);
            ue2::aligned_free_internal(memory);
        }
    }
}
