/*!
 * @file thread_pool_test.cpp
 *
 * @brief Thread_pool unit test source file
 */

#include <unordered_map>
#include <unordered_set>

#include "thread_pool/thread_pool.hpp"
#include "gtest/gtest.h"

class ThreadPoolTest: public ::testing::Test {
public:
    void SetUp() {
        thread_pool = thread_pool::createThreadPool();
    }

    void TearDown() {}

    std::unique_ptr<thread_pool::ThreadPool> thread_pool;
};

TEST(ThreadPoolTest_, CreateThreadPoolError) {
    try {
        auto thread_pool = thread_pool::createThreadPool(0);
    } catch (std::invalid_argument& exception) {
        EXPECT_STREQ(exception.what(), "[thread_pool::createThreadPool] error: "
            "invalid number of threads!");
    }
}

TEST_F(ThreadPoolTest, ParallelCalculation) {

    std::vector<std::vector<std::uint32_t>> data(10);
    for (auto& it: data) {
        it.reserve(100000);
        for (std::uint32_t i = 0; i < 100000; ++i) {
            it.push_back(i);
        }
    }

    auto do_some_calculation = [](std::vector<std::uint32_t>& src) -> void {
        for (std::uint32_t i = 0; i < src.size() - 1; ++i) {
            src[i] = (src[i] * src[i + 1]) / (src[i] - src[i + 1] * 3);
        }
    };

    std::vector<std::future<void>> thread_futures;
    for (std::uint32_t i = 0; i < data.size(); ++i) {
        thread_futures.emplace_back(thread_pool->submit(do_some_calculation,
            std::ref(data[i])));
    }

    for (const auto& it: thread_futures) {
        it.wait();
    }
}

TEST_F(ThreadPoolTest, ThreadIdentifiers) {

    const auto& identifiers = thread_pool->thread_identifiers();
    std::unordered_map<std::thread::id, std::uint32_t> thread_map;
    std::uint32_t thread_id = 0;
    for (const auto& it: identifiers) {
        thread_map[it] = thread_id++;
    }

    EXPECT_EQ(thread_id, thread_map.size());

    auto barrier = thread_pool::createSemaphore(0);
    auto checkpoint = thread_pool::createSemaphore(0);
    auto check_thread_id = [&barrier, &checkpoint](
        std::unordered_map<std::thread::id, std::uint32_t>& thread_map) -> std::int32_t {

        checkpoint->post();
        barrier->wait();

        if (thread_map.count(std::this_thread::get_id()) != 0) {
            return thread_map[std::this_thread::get_id()];
        }
        return -1;
    };

    std::vector<std::future<std::int32_t>> thread_futures;
    for (std::uint32_t i = 0; i < thread_id; ++i) {
        thread_futures.emplace_back(thread_pool->submit(check_thread_id,
            std::ref(thread_map)));
    }

    for (std::uint32_t i = 0; i < thread_id; ++i) {
        checkpoint->wait();
    }
    for (std::uint32_t i = 0; i < thread_id; ++i) {
        barrier->post();
    }

    std::unordered_set<std::int32_t> thread_identifiers;
    for (auto& it: thread_futures) {
        it.wait();
        thread_identifiers.emplace(it.get());
    }

    EXPECT_EQ(thread_id, thread_identifiers.size());
    for (std::uint32_t i = 0; i < thread_id; ++i) {
        EXPECT_EQ(1U, thread_identifiers.count(i));
    }
}
