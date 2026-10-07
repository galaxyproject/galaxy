import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AnonymousUser, AnyUser } from "@/api";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import { useCommandPalette } from "./useCommandPalette";

const REGISTERED_USER = getFakeRegisteredUser();
const ANONYMOUS_USER: AnonymousUser = {
    isAnonymous: true,
    total_disk_usage: 0,
    nice_total_disk_usage: "0.0 bytes",
};

function setupConfig(config: Record<string, unknown>, isLoaded = true) {
    useConfigStore().config = isLoaded ? config : null;
}

function login(user: AnyUser) {
    useUserStore().currentUser = user;
}

describe("useCommandPalette", () => {
    beforeEach(() => {
        createTestingPinia({ createSpy: vi.fn, initialState: { configurationStore: { config: {} } } });
        login(REGISTERED_USER);
        useCommandPalette().closePalette();
    });

    it("shares the open state across all consumers", () => {
        const first = useCommandPalette();
        const second = useCommandPalette();

        expect(first.isPaletteOpen.value).toBe(false);

        first.openPalette();
        expect(second.isPaletteOpen.value).toBe(true);

        second.closePalette();
        expect(first.isPaletteOpen.value).toBe(false);

        first.togglePalette();
        expect(second.isPaletteOpen.value).toBe(true);
    });

    it.each([
        [true, "a registered", REGISTERED_USER, true],
        [true, "an anonymous", ANONYMOUS_USER, true],
        [false, "a registered", REGISTERED_USER, false],
        [false, "an anonymous", ANONYMOUS_USER, false],
    ])("is %s for %s user: %s", (enablePalette, _who, user, expected) => {
        setupConfig({ enable_command_palette: enablePalette });
        login(user);

        expect(useCommandPalette().paletteEnabled.value).toBe(expected);
    });

    it("treats the option as on while it is unset", () => {
        login(ANONYMOUS_USER);

        expect(useCommandPalette().paletteEnabled.value).toBe(true);
    });

    it("stays disabled until the configuration has landed", () => {
        setupConfig({ enable_command_palette: true }, false);

        expect(useCommandPalette().paletteEnabled.value).toBe(false);
    });

    it("refuses to open while it is disabled", () => {
        setupConfig({ enable_command_palette: false });
        const { isPaletteOpen, openPalette, togglePalette } = useCommandPalette();

        openPalette();
        expect(isPaletteOpen.value).toBe(false);

        togglePalette();
        expect(isPaletteOpen.value).toBe(false);
    });
});
