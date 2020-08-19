/*!
 * @file thread_pool.cpp
 *
 * @brief ThreadPool class source file
 */

#include <exception>

#include "thread_pool/thread_pool.hpp"

namespace thread_pool {

std::unique_ptr<Semaphore> createSemaphore(std::uint32_t value) {
    return std::unique_ptr<Semaphore>(new Semaphore(value));
}

std::unique_ptr<ThreadPool> createThreadPool(std::uint32_t num_threads) {
    if (num_threads == 0) {
        throw std::invalid_argument("[thread_pool::createThreadPool] error: "
            "invalid number of threads!");
    }
    return std::unique_ptr<ThreadPool>(new ThreadPool(num_threads));
}

Semaphore::Semaphore(std::uint32_t value)
        : value_(value) {
}

void Semaphore::post() {
    std::unique_lock<std::mutex> lock(mutex_);
    ++value_;
    condition_.notify_one();
}

void Semaphore::wait() {
    std::unique_lock<std::mutex> lock(mutex_);
    condition_.wait(lock, [&](){ return value_; });
    --value_;
}

ThreadPool::ThreadPool(std::uint32_t num_threads) {

    queue_sem_ = createSemaphore(1);
    active_sem_ = createSemaphore(0);

    terminate_ = false;
    for (std::uint32_t i = 0; i < num_threads; ++i) {
        threads_.emplace_back(ThreadPool::worker_thread, this);
        thread_identifiers_.emplace_back(threads_.back().get_id());
    }
}

ThreadPool::~ThreadPool() {

    terminate_ = true;
    for (std::uint32_t i = 0; i < threads_.size(); ++i) {
        active_sem_->post();
    }
    for (auto& it: threads_) {
        it.join();
    }
}

void ThreadPool::worker_thread(ThreadPool* thread_pool) {

    while (true) {
        thread_pool->active_sem_->wait();

        if (thread_pool->terminate_) {
            break;
        }

        thread_pool->queue_sem_->wait();

        auto task = std::move(thread_pool->task_queue_.front());
        thread_pool->task_queue_.pop();

        thread_pool->queue_sem_->post();

        if (thread_pool->terminate_) {
            break;
        }

        task();
    }
}

}
