import { enableAutoUnmount, mount } from "@vue/test-utils";
import type { MaybeRefOrGetter } from "@vueuse/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick, ref } from "vue";

import { useRoundRobinSelector } from "@/composables/roundRobinSelector";

enableAutoUnmount(afterEach);

function mountWithComposable<T>(items: MaybeRefOrGetter<T[]>, pollInterval = 1000) {
    let selection!: ReturnType<typeof useRoundRobinSelector<T>>;

    const TestComponent = defineComponent({
        setup() {
            selection = useRoundRobinSelector(items, pollInterval);
            return () => null;
        },
    });

    mount(TestComponent);
    return selection;
}

function advanceTimersAndTick(ms: number) {
    vi.advanceTimersByTime(ms);
    return nextTick();
}

describe("useRoundRobinSelector", () => {
    beforeEach(() => {
        vi.useFakeTimers();
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
    });

    it("initializes with the first item", async () => {
        const { currentItem } = mountWithComposable(["a", "b", "c"]);
        await nextTick();
        expect(currentItem.value).toBe("a");
    });

    it("advances each polling interval and wraps to the first item", async () => {
        const { currentItem } = mountWithComposable(["x", "y", "z"]);

        await nextTick();
        expect(currentItem.value).toBe("x");

        await advanceTimersAndTick(1000);
        expect(currentItem.value).toBe("y");

        await advanceTimersAndTick(1000);
        expect(currentItem.value).toBe("z");

        await advanceTimersAndTick(1000);
        expect(currentItem.value).toBe("x");
    });

    it("advances manually and wraps to the first item", async () => {
        const { currentItem, next } = mountWithComposable(["apple", "banana"]);

        await nextTick();
        expect(currentItem.value).toBe("apple");

        await next();
        expect(currentItem.value).toBe("banana");

        await next();
        expect(currentItem.value).toBe("apple");
    });

    it("stops interval after stop() is called", async () => {
        const { currentItem, stop } = mountWithComposable(["a", "b", "c"]);

        await nextTick();
        expect(currentItem.value).toBe("a");

        stop();
        await advanceTimersAndTick(3000);

        expect(currentItem.value).toBe("a");
    });

    it("keeps the current item null when an empty list advances", async () => {
        const { currentItem, next } = mountWithComposable([]);

        await nextTick();
        expect(currentItem.value).toBeNull();

        await next();
        expect(currentItem.value).toBeNull();
    });

    it("resets to first item when items change", async () => {
        const items = ref(["apple", "banana"]);
        const { currentItem, next } = mountWithComposable(items);
        await nextTick();
        expect(currentItem.value).toBe("apple");

        items.value = ["cherry", "date"];
        await nextTick();
        expect(currentItem.value).toBe("cherry");
        await next();
        expect(currentItem.value).toBe("date");
    });

    it("starts polling when an empty list receives items", async () => {
        const items = ref<string[]>([]);
        const { currentItem, start } = mountWithComposable(items);
        await nextTick();
        expect(currentItem.value).toBeNull();

        items.value = ["a", "b"];
        start();
        await advanceTimersAndTick(1000);
        expect(currentItem.value).toBe("a");

        await advanceTimersAndTick(1000);
        expect(currentItem.value).toBe("b");
    });

    it("clears the current item when the list becomes empty", async () => {
        const items = ref(["a", "b"]);
        const { currentItem } = mountWithComposable(items);
        await nextTick();
        expect(currentItem.value).toBe("a");

        items.value = [];
        await advanceTimersAndTick(1000);

        expect(currentItem.value).toBeNull();
    });
});
