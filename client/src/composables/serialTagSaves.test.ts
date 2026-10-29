import { deferred } from "@tests/vitest/deferred";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Toast } from "@/composables/toast";

import { useSerialTagSaves } from "./serialTagSaves";

vi.mock("@/composables/toast");

/** Tag saves of one card, with the tags it shows. */
function useCardTags() {
    const card = { tags: [] as string[] };
    const onFailed = vi.fn();
    const { saveTags } = useSerialTagSaves({ setTags: (tags) => (card.tags = tags), onFailed });
    return { card, onFailed, saveTags };
}

describe("useSerialTagSaves", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("shows the tags at once and saves them one after another", async () => {
        const { card, onFailed, saveTags } = useCardTags();
        const firstSave = deferred<string[]>();
        const secondSave = deferred<string[]>();
        const saveFirst = vi.fn(() => firstSave.promise);
        const saveSecond = vi.fn(() => secondSave.promise);

        saveTags(["first"], saveFirst);
        saveTags(["first", "second"], saveSecond);
        await flushPromises();

        expect(card.tags).toEqual(["first", "second"]);
        expect(saveFirst).toHaveBeenCalledTimes(1);
        // an older tag list must never land after a newer one
        expect(saveSecond).not.toHaveBeenCalled();

        firstSave.resolve(["first"]);
        await flushPromises();
        expect(card.tags).toEqual(["first", "second"]);
        expect(saveSecond).toHaveBeenCalledTimes(1);

        secondSave.resolve(["first", "second"]);
        await flushPromises();
        expect(card.tags).toEqual(["first", "second"]);
        expect(onFailed).not.toHaveBeenCalled();
    });

    it("reports a failed save once the queue drains", async () => {
        const { onFailed, saveTags } = useCardTags();

        saveTags(["first"], () => Promise.reject(new Error("save failed")));
        await flushPromises();

        expect(Toast.error).toHaveBeenCalledWith("Failed to save tags: save failed");
        expect(onFailed).toHaveBeenCalledTimes(1);
    });

    it("does not report a failed save that a later save replaced", async () => {
        const { card, onFailed, saveTags } = useCardTags();
        const firstSave = deferred<string[]>();
        const secondSave = deferred<string[]>();

        saveTags(["first"], () => firstSave.promise);
        saveTags(["first", "second"], () => secondSave.promise);

        firstSave.reject(new Error("save failed"));
        await flushPromises();
        expect(Toast.error).toHaveBeenCalledTimes(1);
        // the queued save carries the newest tags, so a reload now could bring back the stored, older ones
        expect(onFailed).not.toHaveBeenCalled();

        secondSave.resolve(["first", "second"]);
        await flushPromises();
        expect(card.tags).toEqual(["first", "second"]);
        expect(onFailed).not.toHaveBeenCalled();
    });

    it("reports a failed last save even after an earlier one succeeded", async () => {
        const { onFailed, saveTags } = useCardTags();

        saveTags(["first"], () => Promise.resolve(["first"]));
        saveTags(["first", "second"], () => Promise.reject(new Error("save failed")));
        await flushPromises();

        expect(onFailed).toHaveBeenCalledTimes(1);
    });

    it("shows the saved tags again when a list reload during the save brought back older ones", async () => {
        const { card, onFailed, saveTags } = useCardTags();
        const save = deferred<string[]>();

        saveTags(["first"], () => save.promise);
        card.tags = [];

        save.resolve(["first"]);
        await flushPromises();

        expect(card.tags).toEqual(["first"]);
        expect(onFailed).not.toHaveBeenCalled();
    });

    it("shows the tags as the server stored them once the queue drains", async () => {
        const { card, onFailed, saveTags } = useCardTags();

        saveTags(["group=liver"], () => Promise.resolve(["group:liver"]));
        await flushPromises();

        expect(card.tags).toEqual(["group:liver"]);
        expect(onFailed).not.toHaveBeenCalled();
    });
});
