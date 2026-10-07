import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";

import { usePersistentToggle } from "./persistentToggle";

describe("usePersistentToggle", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
        localStorage.clear();
    });

    it("starts off by default", () => {
        expect(usePersistentToggle("test-default").toggled.value).toBe(false);
    });

    it("starts at the given initial value and toggles from there", () => {
        const { toggled, toggle } = usePersistentToggle("test-initially-on", true);
        expect(toggled.value).toBe(true);
        toggle();
        expect(toggled.value).toBe(false);
    });
});
