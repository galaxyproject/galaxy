import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { useUserStore } from "@/stores/userStore";

import { useFavoriteObjects } from "./useFavoriteObjects";

vi.mock("@/composables/toast", () => ({ useToast: () => ({ error: vi.fn() }) }));
vi.mock("@/utils/ariaAlert", () => ({ default: vi.fn() }));

describe("useFavoriteObjects", () => {
    it("shares the in-flight guard between consumers", async () => {
        setActivePinia(createPinia());
        const userStore = useUserStore();
        userStore.currentUser = { id: "1", email: "a@b.c", isAnonymous: false } as any;
        let resolve: () => void = () => {};
        const add = vi.fn(() => new Promise<void>((r) => (resolve = r)));
        userStore.addFavoriteTag = add as any;

        const card = useFavoriteObjects();
        const chip = useFavoriteObjects();
        const first = card.toggleFavorite("tags", "alpha");
        expect(chip.isSaving("tags", "alpha")).toBe(true);
        await chip.toggleFavorite("tags", "alpha");
        expect(add).toHaveBeenCalledTimes(1);
        resolve();
        await first;
        expect(chip.isSaving("tags", "alpha")).toBe(false);
    });
});
