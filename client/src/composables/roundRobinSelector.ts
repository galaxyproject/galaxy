import { type MaybeRefOrGetter, toValue } from "@vueuse/core";
import { nextTick, onMounted, onUnmounted, readonly, type Ref, ref, watch } from "vue";

/**
 * Generic round-robin selector for a list of items.
 * @param items - a Ref, computed, or raw array of items to select from
 * @param pollInterval - ms between switching to the next item. Defaults to 10000ms (10 seconds).
 */
export function useRoundRobinSelector<T>(items: MaybeRefOrGetter<T[]> | T[], pollInterval = 10000) {
    let currentIndex = 0;
    let timer: ReturnType<typeof setInterval> | null = null;

    const currentItem = ref<T | null>(null) as Ref<T | null>;

    const getCurrentItem = (): T | null => {
        const itemList = toValue(items);
        if (!itemList.length) {
            return null;
        }
        return itemList[currentIndex % itemList.length] ?? null;
    };

    function updateExposedItem() {
        currentItem.value = getCurrentItem();
    }

    async function next() {
        const itemList = toValue(items);
        if (!itemList.length) {
            currentIndex = 0;
        } else {
            const previousIndex = currentIndex;
            currentIndex = (currentIndex + 1) % itemList.length;
            if (previousIndex === currentIndex) {
                // If we wrapped around to the same index, we still want to trigger a change
                currentItem.value = null;
                await nextTick();
            }
        }
        updateExposedItem();
    }

    function start() {
        stop();
        const itemList = toValue(items);
        if (itemList.length > 0) {
            timer = setInterval(next, pollInterval);
        }
    }

    function stop() {
        if (timer) {
            clearInterval(timer);
            timer = null;
        }
    }

    watch(
        () => toValue(items),
        (newItems) => {
            currentIndex = 0;
            updateExposedItem();
            if (!newItems.length) {
                stop();
            } else if (!timer) {
                start();
            }
        },
    );

    onMounted(() => {
        updateExposedItem();
        start();
    });
    onUnmounted(stop);

    return {
        currentItem: readonly(currentItem),
        start,
        stop,
        next,
    };
}
