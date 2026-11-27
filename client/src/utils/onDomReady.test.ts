import { afterEach, describe, expect, it, vi } from "vitest";

import { onDomReady } from "./onDomReady";

function setReadyState(state: DocumentReadyState) {
    vi.spyOn(document, "readyState", "get").mockReturnValue(state);
}

describe("onDomReady", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it.each<DocumentReadyState>(["interactive", "complete"])("runs immediately when the document is %s", (state) => {
        setReadyState(state);
        const callback = vi.fn();
        onDomReady(callback);
        expect(callback).toHaveBeenCalledTimes(1);
    });

    it("waits for DOMContentLoaded and runs once while the document is loading", () => {
        setReadyState("loading");
        const callback = vi.fn();
        onDomReady(callback);
        expect(callback).not.toHaveBeenCalled();

        document.dispatchEvent(new Event("DOMContentLoaded"));
        document.dispatchEvent(new Event("DOMContentLoaded"));
        expect(callback).toHaveBeenCalledTimes(1);
    });

    it("does not run again when the window load event fires", () => {
        setReadyState("interactive");
        const callback = vi.fn();
        onDomReady(callback);
        expect(callback).toHaveBeenCalledTimes(1);
        window.dispatchEvent(new Event("load"));
        expect(callback).toHaveBeenCalledTimes(1);
    });
});
