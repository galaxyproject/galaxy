import type { Config } from "dompurify";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { PROFILE_CONFIGS, sanitizeHtml } from "@/directives/sanitizeHtml";

// The global test setup replaces this module with a pass-through spy; these
// tests exercise the real profiles against a DOMPurify stand-in instead.
vi.unmock("@/directives/sanitizeHtml");

const { defaultInstance, linksInstance, createInstance } = vi.hoisted(() => {
    const makeInstance = () => ({
        sanitize: vi.fn((html: string, _config?: Config) => `clean(${html})`),
        addHook: vi.fn(),
    });
    const defaultInstance = makeInstance();
    const linksInstance = makeInstance();
    return { defaultInstance, linksInstance, createInstance: vi.fn(() => linksInstance) };
});

vi.mock("dompurify", () => ({ default: Object.assign(createInstance, defaultInstance) }));

type Hook = (node: Node) => void;

function linksHook(): Hook {
    sanitizeHtml("", "links");
    const calls = linksInstance.addHook.mock.calls;
    expect(calls).toHaveLength(1);
    expect(calls[0]![0]).toBe("afterSanitizeAttributes");
    return calls[0]![1] as Hook;
}

describe("sanitizeHtml", () => {
    beforeEach(() => {
        defaultInstance.sanitize.mockClear();
        linksInstance.sanitize.mockClear();
    });

    test("default profile uses the shared DOMPurify instance with the HTML profile", () => {
        expect(sanitizeHtml("<b>x</b>")).toBe("clean(<b>x</b>)");
        expect(defaultInstance.sanitize).toHaveBeenCalledWith("<b>x</b>", {
            USE_PROFILES: { html: true },
            FORBID_TAGS: ["style", "form", "input", "button", "textarea", "select"],
        });
        expect(linksInstance.sanitize).not.toHaveBeenCalled();
    });

    test("null and undefined are sanitized as empty strings", () => {
        sanitizeHtml(null);
        sanitizeHtml(undefined);
        expect(defaultInstance.sanitize.mock.calls.map((call) => call[0])).toEqual(["", ""]);
    });

    test("links profile keeps target and uses its own DOMPurify instance", () => {
        expect(sanitizeHtml("<a>x</a>", "links")).toBe("clean(<a>x</a>)");
        expect(createInstance).toHaveBeenCalledTimes(1);
        expect(linksInstance.sanitize).toHaveBeenCalledWith("<a>x</a>", {
            USE_PROFILES: { html: true },
            FORBID_TAGS: ["style", "form", "input", "button", "textarea", "select"],
            ADD_ATTR: ["target"],
        });
        expect(defaultInstance.sanitize).not.toHaveBeenCalled();
    });

    test("markdown profile shares the links instance and allows Galaxy's URI schemes, SVG and MathML", () => {
        expect(sanitizeHtml("md", "markdown")).toBe("clean(md)");
        expect(defaultInstance.sanitize).not.toHaveBeenCalled();
        const config = linksInstance.sanitize.mock.calls[0]![1]!;
        expect(config.USE_PROFILES).toEqual({ html: true, svg: true, mathMl: true });
        expect(config.ADD_ATTR).toEqual(["target"]);
        expect(config.ADD_TAGS).toEqual(["semantics", "annotation"]);
        // The authoring help renders copy buttons, so only <style> is dropped here
        expect(config.FORBID_TAGS).toEqual(["style"]);
        const uriPattern = config.ALLOWED_URI_REGEXP!;
        for (const uri of [
            "gxhelp://term",
            "gxstatic://image.png",
            "gxdatasetasimage://abc123",
            "https://x",
            "/relative",
        ]) {
            expect(uriPattern.test(uri)).toBe(true);
        }
        for (const uri of ["javascript:void(0)", "data:text/html,x", "vbscript:x"]) {
            expect(uriPattern.test(uri)).toBe(false);
        }
    });

    test("the rel hook is only added to the links instance, once", () => {
        sanitizeHtml("a", "links");
        sanitizeHtml("b", "links");
        sanitizeHtml("c", "markdown");
        sanitizeHtml("d");
        expect(createInstance).toHaveBeenCalledTimes(1);
        expect(linksInstance.addHook).toHaveBeenCalledTimes(1);
        expect(defaultInstance.addHook).not.toHaveBeenCalled();
    });

    test("targets that open a new window get noopener and noreferrer", () => {
        const hook = linksHook();
        for (const target of ["_blank", "_BLANK", "report"]) {
            const link = document.createElement("a");
            link.setAttribute("target", target);
            hook(link);
            expect(link.getAttribute("rel")).toBe("noopener noreferrer");
        }
    });

    test("an existing rel value is kept and not duplicated", () => {
        const hook = linksHook();
        const link = document.createElement("a");
        link.setAttribute("target", "_blank");
        link.setAttribute("rel", "nofollow  noopener");
        hook(link);
        expect(link.getAttribute("rel")).toBe("nofollow noopener noreferrer");
    });

    test("elements without a target, same-window targets and non-element nodes are left alone", () => {
        const hook = linksHook();
        const link = document.createElement("a");
        hook(link);
        expect(link.hasAttribute("rel")).toBe(false);
        for (const target of ["_self", "_top", "_parent"]) {
            const sameWindow = document.createElement("a");
            sameWindow.setAttribute("target", target);
            hook(sameWindow);
            expect(sameWindow.hasAttribute("rel")).toBe(false);
        }
        const text = document.createTextNode("plain");
        expect(() => hook(text)).not.toThrow();
    });

    test("unknown profiles are rejected", () => {
        expect(() => sanitizeHtml("x", "nope" as never)).toThrow("Unknown v-sanitize-html profile: nope");
    });

    test("profile configs are not shared objects that DOMPurify could mutate across profiles", () => {
        expect(PROFILE_CONFIGS.default).not.toBe(PROFILE_CONFIGS.links);
        expect(PROFILE_CONFIGS.default).not.toHaveProperty("ADD_ATTR");
    });
});
