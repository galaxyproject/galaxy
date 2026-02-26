import { beforeEach, describe, expect, it, vi } from "vitest";

import { copyLink } from "./utilities";

const writeText = vi.fn();

Object.defineProperty(navigator, "clipboard", {
    writable: true,
    configurable: true,
    value: {
        writeText,
    },
});

describe("copyLink", () => {
    beforeEach(() => {
        writeText.mockClear();
        (navigator.clipboard.writeText as ReturnType<typeof vi.fn>).mockResolvedValue(undefined);
    });

    it("should copy the link to the clipboard", () => {
        const toolId = "MyToolId";
        copyLink(toolId);
        expect(writeText).toHaveBeenCalledTimes(1);
        expect(writeText).toHaveBeenCalledWith(expect.stringContaining(toolId));
    });

    it("should encode the tool id with spaces", () => {
        const toolId = "My Tool Id";
        copyLink(toolId);
        expect(writeText).toHaveBeenCalledTimes(1);
        expect(writeText).toHaveBeenCalledWith(expect.stringContaining("My%20Tool%20Id"));
    });

    it("should not encode the character '+' in the tool id", () => {
        const toolId = "My Tool Id+1";
        copyLink(toolId);
        expect(writeText).toHaveBeenCalledTimes(1);
        expect(writeText).toHaveBeenCalledWith(expect.stringContaining("My%20Tool%20Id+1"));
    });
});
