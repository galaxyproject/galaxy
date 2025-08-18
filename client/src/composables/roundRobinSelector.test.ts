import { jest } from "@jest/globals";
import { mount } from "@vue/test-utils";
import type { MaybeRefOrGetter } from "@vueuse/core";
import { defineComponent, nextTick, ref } from "vue";

import { useRoundRobinSelector } from "@/composables/roundRobinSelector";

jest.useFakeTimers();

function mountWithComposable<T>(items: MaybeRefOrGetter<T[]>, pollInterval = 1000) {
    const exposed = {
        currentItem: ref<T | null>(null),
        next: () => {},
        stop: () => {},
        start: () => {},
    };

    const TestComponent = defineComponent({
        setup() {
            const result = useRoundRobinSelector(items, pollInterval);
            Object.assign(exposed, result);
            return () => null; // no template/render needed
        },
    });

    mount(TestComponent);
    return exposed;
}

function advanceTimersAndTick(ms: number) {
    jest.advanceTimersByTime(ms);
    return nextTick();
}

describe("useRoundRobinSelector", () => {
    afterEach(() => {
        jest.clearAllTimers();
    });

    it("initializes with the first item", async () => {
        const { currentItem } = mountWithComposable(["a", "b", "c"]);
        await nextTick();
        expect(currentItem.value).toBe("a");
    });

    it("cycles through items over time", async () => {
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

    it("can manually go to next item", async () => {
        const { currentItem, next } = mountWithComposable(["apple", "banana"]);

        await nextTick();
        expect(currentItem.value).toBe("apple");

        next();
        expect(currentItem.value).toBe("banana");

        next();
        expect(currentItem.value).toBe("apple");
    });

    it("stops interval after stop() is called", async () => {
        const { currentItem, stop } = mountWithComposable(["a", "b", "c"]);

        await nextTick();
        expect(currentItem.value).toBe("a");

        stop();
        await advanceTimersAndTick(3000);

        expect(currentItem.value).toBe("a"); // unchanged
    });

    it("handles empty list", async () => {
        const { currentItem, next } = mountWithComposable([]);

        await nextTick();
        expect(currentItem.value).toBe(null);

        next();
        expect(currentItem.value).toBe(null);
    });

    it("resets to first item when items change", async () => {
        const items = ref(["apple", "banana"]);
        const { currentItem, next } = mountWithComposable(items);
        await nextTick();
        expect(currentItem.value).toBe("apple");

        items.value = ["cherry", "date"];
        await nextTick();
        expect(currentItem.value).toBe("cherry");
        next();
        expect(currentItem.value).toBe("date");
    });

    it("starts interval when items are added", async () => {
        const items = ref<string[]>([]);
        const { currentItem, start } = mountWithComposable(items);
        await nextTick();
        expect(currentItem.value).toBe(null);

        items.value = ["a", "b"];
        start();
        await advanceTimersAndTick(1000);
        expect(currentItem.value).toBe("a");

        await advanceTimersAndTick(1000);
        expect(currentItem.value).toBe("b");
    });

    it("stops interval when items are cleared", async () => {
        const items = ref(["a", "b"]);
        const { currentItem } = mountWithComposable(items);
        await nextTick();
        expect(currentItem.value).toBe("a");

        items.value = [];
        await advanceTimersAndTick(1000);

        expect(currentItem.value).toBe(null); // should not change
    });
});
