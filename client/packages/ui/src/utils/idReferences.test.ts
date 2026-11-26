import { describe, expect, test } from "vitest";

import { addIdReference, removeIdReference } from "./idReferences";

describe("idReferences", () => {
    test("adds an id once and keeps the existing ids", () => {
        const el = document.createElement("input");
        addIdReference(el, "aria-describedby", "tooltip");
        expect(el.getAttribute("aria-describedby")).toBe("tooltip");

        el.setAttribute("aria-describedby", " help   error ");
        addIdReference(el, "aria-describedby", "tooltip");
        addIdReference(el, "aria-describedby", "tooltip");
        expect(el.getAttribute("aria-describedby")).toBe("help error tooltip");
    });

    test("removes only the given id, and the attribute with the last id", () => {
        const el = document.createElement("input");
        el.setAttribute("aria-describedby", "help tooltip tooltip-2");
        removeIdReference(el, "aria-describedby", "tooltip");
        expect(el.getAttribute("aria-describedby")).toBe("help tooltip-2");

        removeIdReference(el, "aria-describedby", "help");
        removeIdReference(el, "aria-describedby", "tooltip-2");
        expect(el.hasAttribute("aria-describedby")).toBe(false);
    });
});
