import { createTestingPinia } from "@pinia/testing";
import { getFakeAnonymousUser, getFakeRegisteredUser } from "@tests/test-data";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AnyUser } from "@/api";
import { useConfigStore } from "@/stores/configurationStore";
import { useUserStore } from "@/stores/userStore";

import { useCommandPalette } from "./useCommandPalette";

function loadConfig(config: Record<string, unknown>) {
    useConfigStore().config = config;
}

function login(user: AnyUser) {
    useUserStore().currentUser = user;
}

describe("useCommandPalette", () => {
    beforeEach(() => {
        createTestingPinia({ createSpy: vi.fn, initialState: { configurationStore: { config: {} } } });
        login(getFakeRegisteredUser());
        // The open state is shared module state, so it outlives each test's pinia.
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
        [true, true, "registered", getFakeRegisteredUser()],
        [true, true, "anonymous", getFakeAnonymousUser()],
        [false, false, "registered", getFakeRegisteredUser()],
        [false, false, "anonymous", getFakeAnonymousUser()],
    ])("with enable_command_palette %s, paletteEnabled is %s for %s users", (enablePalette, expected, _who, user) => {
        loadConfig({ enable_command_palette: enablePalette });
        login(user);

        expect(useCommandPalette().paletteEnabled.value).toBe(expected);
    });

    it("treats the option as on while it is unset", () => {
        loadConfig({});
        login(getFakeAnonymousUser());

        expect(useCommandPalette().paletteEnabled.value).toBe(true);
    });

    it("stays disabled and refuses to open until the configuration has loaded", () => {
        useConfigStore().config = null;
        const { isPaletteOpen, paletteEnabled, openPalette } = useCommandPalette();

        expect(paletteEnabled.value).toBe(false);

        openPalette();
        expect(isPaletteOpen.value).toBe(false);
    });

    it("refuses to open while it is disabled", () => {
        loadConfig({ enable_command_palette: false });
        const { isPaletteOpen, openPalette, togglePalette } = useCommandPalette();

        openPalette();
        expect(isPaletteOpen.value).toBe(false);

        togglePalette();
        expect(isPaletteOpen.value).toBe(false);
    });
});
