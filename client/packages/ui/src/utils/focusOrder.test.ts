import { afterEach, describe, expect, it, vi } from "vitest";

import { nextTabbableAfter, tabbableElements } from "./focusOrder";

function render(html: string) {
    document.body.innerHTML = html;
}

function byId(id: string) {
    return document.getElementById(id)!;
}

afterEach(() => {
    document.body.innerHTML = "";
});

describe("tabbableElements", () => {
    it("lists the elements Tab stops on in document order", () => {
        render(`
            <a id="link" href="#">link</a>
            <a id="anchor">no href</a>
            <button id="button">button</button>
            <button id="disabled" disabled>disabled</button>
            <input id="hidden-input" type="hidden" />
            <span id="span" tabindex="0">span</span>
            <span id="removed" tabindex="-1">removed</span>
            <a id="removed-link" href="#" tabindex="-1">removed link</a>
        `);

        expect(tabbableElements(document.body).map((element) => element.id)).toEqual(["link", "button", "span"]);
    });

    it("skips disabled controls that a tabindex would otherwise let in", () => {
        render(`<button id="disabled" disabled tabindex="0">disabled</button><button id="enabled">enabled</button>`);

        expect(tabbableElements(document.body).map((element) => element.id)).toEqual(["enabled"]);
    });

    it("skips inert content", () => {
        render(`<div inert><button>inert</button></div><button id="live">live</button>`);

        expect(tabbableElements(document.body).map((element) => element.id)).toEqual(["live"]);
    });

    it("skips elements that are not rendered", () => {
        render(`<button id="shown">shown</button><button id="collapsed" style="display: none">collapsed</button>`);

        expect(tabbableElements(document.body).map((element) => element.id)).toEqual(["shown"]);
    });
});

describe("nextTabbableAfter", () => {
    it("finds the next element after the anchor, not inside it", () => {
        render(`
            <button id="before">before</button>
            <span id="anchor"><button id="inside">inside</button></span>
            <p>text</p>
            <a id="after" href="#">after</a>
        `);

        expect(nextTabbableAfter(byId("anchor"), document.body)?.id).toBe("after");
    });

    it("passes over elements skip() rejects", () => {
        render(
            `<button id="anchor">anchor</button><button id="skipped">skipped</button><button id="next">next</button>`,
        );

        expect(nextTabbableAfter(byId("anchor"), document.body, (element) => element.id === "skipped")?.id).toBe(
            "next",
        );
    });

    it("checks the visibility of candidates after the anchor only", () => {
        render(
            `<button id="before">before</button><button id="anchor">anchor</button><button id="after">after</button>`,
        );
        const before = vi.spyOn(byId("before"), "checkVisibility");

        expect(nextTabbableAfter(byId("anchor"), document.body)?.id).toBe("after");
        expect(before).not.toHaveBeenCalled();
    });

    it("stays within the root", () => {
        render(`<div id="root"><button id="anchor">anchor</button></div><button id="outside">outside</button>`);

        expect(nextTabbableAfter(byId("anchor"), byId("root"))).toBeUndefined();
    });
});
