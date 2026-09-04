import { afterEach, describe, expect, it } from "vitest";

import { activeToastHost, registerToastHost, unregisterToastHost } from "./toastHost";

const firstHost = "first-modal";
const secondHost = "second-modal";

afterEach(() => {
    unregisterToastHost(firstHost);
    unregisterToastHost(secondHost);
});

describe("toastHost", () => {
    it("uses the most recently opened modal as the active toast host", () => {
        registerToastHost(firstHost);
        registerToastHost(secondHost);

        expect(activeToastHost.value).toBe(secondHost);
    });

    it("restores the prior modal host when the active modal closes", () => {
        registerToastHost(firstHost);
        registerToastHost(secondHost);
        unregisterToastHost(secondHost);

        expect(activeToastHost.value).toBe(firstHost);
    });
});
