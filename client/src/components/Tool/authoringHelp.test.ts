import { describe, expect, it } from "vitest";

import {
    authoringHelpGroups,
    authoringHelpIntro,
    authoringHelpSections,
    authoringHelpTitle,
    resolveDocLinks,
} from "./authoringHelp";

describe("user-defined tool authoring help", () => {
    it("loads the shared help content", () => {
        expect(authoringHelpTitle).toBe("Authoring User-Defined Tools");
        expect(authoringHelpIntro).toContain("User-defined tools let a user register");
        expect(authoringHelpSections.length).toBeGreaterThan(0);
        expect(new Set(authoringHelpSections.map((section) => section.id)).size).toBe(authoringHelpSections.length);
        expect(authoringHelpGroups.map((group) => group.title)).toEqual(["Reference", "Common questions"]);
        expect(authoringHelpGroups.every((group) => group.sections.length > 0)).toBe(true);
    });

    it("resolves Galaxy documentation links for the editor", () => {
        const input = "[Tool schema](gxdoc:dev/schema.md)";

        expect(resolveDocLinks(input)).toBe("[Tool schema](https://docs.galaxyproject.org/en/master/dev/schema.html)");
    });

    it("does not leave unresolved documentation links in rendered content", () => {
        expect(authoringHelpIntro).not.toContain("gxdoc:");
        for (const section of authoringHelpSections) {
            expect(section.body).not.toContain("gxdoc:");
        }
    });
});
