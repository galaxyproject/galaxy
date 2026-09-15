import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { setupMockConfig } from "@tests/vitest/mockConfig";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AnonymousUser, AnyUser } from "@/api";
import { useUserStore } from "@/stores/userStore";

import { useCommandPalette } from "./useCommandPalette";

const REGISTERED_USER = getFakeRegisteredUser();
const ANONYMOUS_USER: AnonymousUser = {
    isAnonymous: true,
    total_disk_usage: 0,
    nice_total_disk_usage: "0.0 bytes",
};

function login(user: AnyUser) {
    useUserStore().currentUser = user;
}

describe("useCommandPalette", () => {
    beforeEach(() => {
        createTestingPinia({ createSpy: vi.fn });
        setupMockConfig({});
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
        [true, true, "a registered", REGISTERED_USER, true],
        [true, true, "an anonymous", ANONYMOUS_USER, true],
        [true, false, "a registered", REGISTERED_USER, true],
        [true, false, "an anonymous", ANONYMOUS_USER, false],
        [false, true, "a registered", REGISTERED_USER, false],
        [false, true, "an anonymous", ANONYMOUS_USER, false],
        [false, false, "a registered", REGISTERED_USER, false],
        [false, false, "an anonymous", ANONYMOUS_USER, false],
    ])("is %s with anonymous access %s for %s user: %s", (enablePalette, allowAnonymous, _who, user, expected) => {
        setupMockConfig({
            enable_command_palette: enablePalette,
            command_palette_allow_anonymous: allowAnonymous,
        });
        login(user);

        expect(useCommandPalette().paletteEnabled.value).toBe(expected);
    });

    it("treats both options as on while they are unset", () => {
        login(ANONYMOUS_USER);

        expect(useCommandPalette().paletteEnabled.value).toBe(true);
    });

    it("stays disabled until the configuration has landed", () => {
        setupMockConfig({ enable_command_palette: true }, false);

        expect(useCommandPalette().paletteEnabled.value).toBe(false);
    });

    it("refuses to open while it is disabled", () => {
        setupMockConfig({ enable_command_palette: false });
        const { isPaletteOpen, openPalette, togglePalette } = useCommandPalette();

        openPalette();
        expect(isPaletteOpen.value).toBe(false);

        togglePalette();
        expect(isPaletteOpen.value).toBe(false);
    });

    it("revokes access the moment the user turns anonymous", () => {
        setupMockConfig({ command_palette_allow_anonymous: false });
        const { paletteEnabled } = useCommandPalette();

        expect(paletteEnabled.value).toBe(true);

        login(ANONYMOUS_USER);

        expect(paletteEnabled.value).toBe(false);
    });
});
