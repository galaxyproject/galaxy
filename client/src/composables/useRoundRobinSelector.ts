import { computed, onMounted, onUnmounted, readonly, type Ref, ref, watch } from "vue";

/**
 * Generic round-robin selector for a list of items.
 * @param items - a Ref or computed returning the current list of items to select from
 * @param pollInterval - ms between switching to the next item. Defaults to 10000ms (10 seconds).
 */
export function useRoundRobinSelector<T>(items: Ref<T[]>, pollInterval = 10000) {
    const currentIndex = ref(0);
    const timer = ref<ReturnType<typeof setInterval> | null>(null);

    const currentItem = computed(() => {
        if (!items.value.length) {
            return null;
        }
        return items.value[currentIndex.value % items.value.length];
    });

    function next() {
        if (!items.value.length) {
            currentIndex.value = 0;
        } else {
            currentIndex.value = (currentIndex.value + 1) % items.value.length;
        }
    }

    function start() {
        stop();
        timer.value = setInterval(next, pollInterval);
    }

    function stop() {
        if (timer.value) {
            clearInterval(timer.value);
            timer.value = null;
        }
    }

    // Reset index if items change
    watch(items, () => {
        currentIndex.value = 0;
    });

    onMounted(start);
    onUnmounted(stop);

    return {
        currentItem: readonly(currentItem),
        start,
        stop,
        next,
    };
}
