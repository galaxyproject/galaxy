import { describe, expect, it } from "vitest";

import { flattenSectionedValues, groupInputsIntoSections, stripSectionPrefix } from "./inputSections";

function input(name: string, extra: Record<string, unknown> = {}) {
    return { name, optional: true, ...extra };
}

describe("groupInputsIntoSections", () => {
    it("returns the inputs unchanged without section assignments", () => {
        const inputs = [input("0"), input("1")];
        expect(groupInputsIntoSections(inputs, [{ name: "advanced" }], new Map())).toBe(inputs);
    });

    it("keeps members in input order, even when the section's members are not adjacent", () => {
        const grouped = groupInputsIntoSections(
            [input("0"), input("1"), input("2"), input("3")],
            [{ name: "advanced", label: "Advanced" }],
            new Map([
                ["0", "advanced"],
                ["2", "advanced"],
            ]),
        );
        expect(grouped.map((entry) => ("inputs" in entry ? entry.inputs.map((i) => i.name) : entry.name))).toEqual([
            ["0", "2"],
            "1",
            "3",
        ]);
    });

    it("opens a collapsed section holding a required input without a value", () => {
        const sections = [{ name: "advanced", expanded: false }];
        const sectionOf = new Map([["0", "advanced"]]);
        const open = (extra: Record<string, unknown>) =>
            (groupInputsIntoSections([input("0", extra)], sections, sectionOf)[0] as { expanded: boolean }).expanded;
        expect(open({ optional: true })).toBe(false);
        expect(open({ optional: false, value: 3 })).toBe(false);
        expect(open({ optional: false, value: { values: [{ id: "x", src: "hda" }] } })).toBe(false);
        expect(open({ optional: false })).toBe(true);
        expect(open({ optional: false, value: "" })).toBe(true);
        expect(open({ optional: false, value: { values: [] } })).toBe(true);
    });

    it("matches step index names given as String objects", () => {
        const grouped = groupInputsIntoSections(
            [{ name: new String("4"), optional: true }],
            [],
            new Map([["4", "references"]]),
        );
        expect(grouped[0]).toMatchObject({ type: "section", name: "references", title: "references" });
    });
});

describe("section prefixes", () => {
    it("strips only known section prefixes", () => {
        expect(stripSectionPrefix("advanced|3", ["advanced"])).toBe("3");
        expect(stripSectionPrefix("other|3", ["advanced"])).toBe("other|3");
        expect(stripSectionPrefix("3", ["advanced"])).toBe("3");
    });

    it("flattens form values", () => {
        expect(flattenSectionedValues({ 0: "a", "advanced|1": "b" }, ["advanced"])).toEqual({ 0: "a", 1: "b" });
    });
});
