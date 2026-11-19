import { describe, expect, it } from "vitest";

import type { FormInputNode } from "@/components/Form/composables/useFormState";

import {
    buildClearPayload,
    buildInputs,
    buildPayload,
    clearableSecrets,
    dirtySections,
    type ExtraPreferenceSection,
    type ExtraPreferenceValues,
    formKey,
    isRequiredMissing,
    missingRequiredInputs,
} from "./extraPreferencesForm";

const definition: ExtraPreferenceSection[] = [
    {
        name: "cloud",
        description: "Cloud storage",
        inputs: [
            { name: "endpoint", label: "Endpoint", type: "text", required: true, multiple: false },
            { name: "token", label: "Token", type: "secret", required: false, store: "vault", multiple: false },
            { name: "api_key", label: "API key", type: "password", required: true, multiple: false },
            { name: "port", label: "Port", type: "integer", required: false, multiple: false },
            { name: "ratio", label: "Ratio", type: "float", required: false, multiple: false },
            { name: "verify", label: "Verify TLS", type: "boolean", required: false, multiple: false },
            {
                name: "region",
                label: "Region",
                options: [
                    ["EU", "eu"],
                    ["US", "us"],
                ],
                required: false,
                multiple: false,
            },
            {
                name: "zones",
                label: "Zones",
                type: "select",
                options: [
                    ["A", "a"],
                    ["B", "b"],
                ],
                required: false,
                multiple: true,
            },
            { name: "note", label: "Note", required: false, multiple: false, value: "none" },
        ],
    },
];

const values: ExtraPreferenceValues = {
    cloud: {
        endpoint: "https://example.org",
        token: { is_set: true },
        api_key: { is_set: false },
        port: 8080,
        ratio: null,
        verify: true,
        region: "eu",
        zones: ["a"],
        note: "none",
    },
};

function leaves(nodes: FormInputNode[]): FormInputNode[] {
    return nodes.flatMap((node) => node.inputs ?? [node]);
}

function leaf(name: string, source = values): FormInputNode {
    const found = leaves(buildInputs(definition, source)).find((node) => node.name === name);
    expect(found).toBeDefined();
    return found as FormInputNode;
}

/** The form data a form emits when the user changed nothing. */
function untouched(source = values): Record<string, unknown> {
    const data: Record<string, unknown> = {};
    for (const section of buildInputs(definition, source)) {
        for (const node of section.inputs ?? []) {
            data[formKey(section.name, node.name)] = node.value;
        }
    }
    return data;
}

describe("buildInputs", () => {
    it("makes one expanded section per definition section", () => {
        const [section, ...rest] = buildInputs(definition, values);
        expect(rest).toHaveLength(0);
        expect(section).toMatchObject({ type: "section", name: "cloud", title: "Cloud storage", expanded: true });
        expect(section?.inputs).toHaveLength(definition[0]!.inputs!.length);
    });

    it("maps secret and password to masked inputs with an empty value", () => {
        expect(leaf("token")).toMatchObject({ type: "password", value: "" });
        expect(leaf("api_key")).toMatchObject({ type: "password", value: "" });
    });

    it("never carries a stored or default secret value", () => {
        const withDefault: ExtraPreferenceSection[] = [
            {
                name: "s",
                description: "S",
                inputs: [{ name: "k", type: "secret", required: false, multiple: false, value: "leaked" }],
            },
        ];
        const [section] = buildInputs(withDefault, { s: { k: { is_set: true } } });
        expect(JSON.stringify(section)).not.toContain("leaked");
        expect(section?.inputs?.[0]?.value).toBe("");
    });

    it("hints that a stored secret is kept when left empty", () => {
        expect(leaf("token").help).toContain("A value is stored");
        expect(leaf("api_key").help ?? "").not.toContain("A value is stored");
    });

    it("keeps the admin help text next to the hint", () => {
        const helped: ExtraPreferenceSection[] = [
            {
                name: "s",
                description: "S",
                inputs: [{ name: "k", type: "secret", help: "From the console.", required: false, multiple: false }],
            },
        ];
        const [section] = buildInputs(helped, { s: { k: { is_set: true } } });
        expect(section?.inputs?.[0]?.help).toMatch(/^From the console\. .*A value is stored/);
    });

    it("marks every required input as required, a stored required secret included", () => {
        expect(leaf("token").optional).toBe(true);
        // a stored required secret is not missing when left empty, but it is still required
        const stored = { cloud: { ...values.cloud, api_key: { is_set: true } } };
        expect(leaf("api_key", stored).optional).toBe(false);
        expect(leaf("api_key").optional).toBe(false);
        expect(leaf("endpoint").optional).toBe(false);
        expect(leaf("port").optional).toBe(true);
    });

    it("types inputs the way the server does when `type` is missing", () => {
        expect(leaf("region").type).toBe("select");
        expect(leaf("note").type).toBe("text");
    });

    it("shows stored values and falls back to the definition default, then to an empty value", () => {
        expect(leaf("endpoint").value).toBe("https://example.org");
        expect(leaf("port").value).toBe(8080);
        expect(leaf("verify").value).toBe(true);
        expect(leaf("zones").value).toEqual(["a"]);
        expect(leaf("note").value).toBe("none");
        const unset: ExtraPreferenceValues = {
            cloud: Object.fromEntries(Object.keys(values.cloud!).map((name) => [name, null])),
        };
        expect(leaf("endpoint", unset).value).toBe("");
        expect(leaf("verify", unset).value).toBe(false);
        expect(leaf("zones", unset).value).toEqual([]);
        expect(leaf("port", unset).value).toBeNull();
        expect(leaf("region", unset).value).toBeNull();
    });

    it("passes select options and the multiple flag to the form", () => {
        expect(leaf("zones")).toMatchObject({
            multiple: true,
            options: [
                ["A", "a"],
                ["B", "b"],
            ],
        });
    });

    it("starts an unset required single select on its first option, as the select widget does", () => {
        const picked: ExtraPreferenceSection[] = [
            {
                name: "s",
                description: "S",
                inputs: [
                    { name: "a", type: "select", options: [["One", "1"]], required: true, multiple: false },
                    { name: "b", type: "select", options: [["One", "1"]], required: false, multiple: false },
                    { name: "c", type: "select", options: [["One", "1"]], required: true, multiple: true },
                ],
            },
        ];
        const [section] = buildInputs(picked, { s: { a: null, b: null, c: null } });
        expect(section?.inputs?.map((node) => node.value)).toEqual(["1", null, []]);
    });

    it("builds nodes that do not share state with the definition", () => {
        const node = leaf("zones");
        (node.value as string[]).push("b");
        expect(leaf("zones").value).toEqual(["a"]);
    });
});

describe("buildPayload", () => {
    it("is empty when nothing changed", () => {
        expect(buildPayload(definition, values, untouched())).toEqual({});
    });

    it("sends the defaults of an edited section, left as they are or typed back in", () => {
        const unset: ExtraPreferenceValues = { cloud: { ...values.cloud!, note: null } };
        const edited = { ...untouched(unset), [formKey("cloud", "endpoint")]: "https://other.example.org" };
        expect(buildPayload(definition, unset, edited)).toEqual({
            cloud: { endpoint: "https://other.example.org", note: "none" },
        });
        const typed = { ...edited, [formKey("cloud", "note")]: "none" };
        expect(buildPayload(definition, unset, typed)).toEqual({
            cloud: { endpoint: "https://other.example.org", note: "none" },
        });
    });

    it("sends nothing for an untouched default, or one typed back without another edit", () => {
        const unset: ExtraPreferenceValues = { cloud: { ...values.cloud!, note: null } };
        expect(buildPayload(definition, unset, untouched(unset))).toEqual({});
        const typed = { ...untouched(unset), [formKey("cloud", "note")]: "none" };
        expect(buildPayload(definition, unset, typed)).toEqual({});
    });

    it("does not send a default that is already stored, and clears a stored value that was emptied", () => {
        const emptied = { ...untouched(), [formKey("cloud", "note")]: "" };
        expect(buildPayload(definition, values, emptied)).toEqual({ cloud: { note: null } });
    });

    it("does not send an unset boolean without a default that was not touched", () => {
        const unset: ExtraPreferenceValues = { cloud: { ...values.cloud!, verify: null } };
        expect(buildPayload(definition, unset, untouched(unset))).toEqual({});
    });

    it("sends only the changed inputs, grouped by section", () => {
        const data = { ...untouched(), [formKey("cloud", "endpoint")]: "https://other.example.org" };
        expect(buildPayload(definition, values, data)).toEqual({ cloud: { endpoint: "https://other.example.org" } });
    });

    it("omits an empty secret, whether stored or not", () => {
        const data = { ...untouched(), [formKey("cloud", "token")]: "", [formKey("cloud", "api_key")]: "" };
        expect(buildPayload(definition, values, data)).toEqual({});
    });

    it("sends a typed secret unchanged, without trimming", () => {
        const data = { ...untouched(), [formKey("cloud", "token")]: "  s3cret " };
        expect(buildPayload(definition, values, data)).toEqual({ cloud: { token: "  s3cret " } });
    });

    it("trims other text and sends an emptied optional input as null", () => {
        const data = {
            ...untouched(),
            [formKey("cloud", "endpoint")]: "  https://a.example.org ",
            [formKey("cloud", "port")]: "",
        };
        expect(buildPayload(definition, values, data)).toEqual({
            cloud: { endpoint: "https://a.example.org", port: null },
        });
    });

    it("does not send an unset optional input that stays empty", () => {
        const unset: ExtraPreferenceValues = { cloud: { ...values.cloud!, ratio: null, region: null } };
        const data = { ...untouched(unset), [formKey("cloud", "ratio")]: "", [formKey("cloud", "region")]: null };
        expect(buildPayload(definition, unset, data)).toEqual({});
    });

    it("coerces numbers and booleans to the declared kind", () => {
        const data = {
            ...untouched(),
            [formKey("cloud", "port")]: "9090",
            [formKey("cloud", "ratio")]: "0.5",
            [formKey("cloud", "verify")]: "false",
        };
        expect(buildPayload(definition, values, data)).toEqual({ cloud: { port: 9090, ratio: 0.5, verify: false } });
    });

    it("sends a number that did not change as nothing, even when the form gives a string", () => {
        const data = { ...untouched(), [formKey("cloud", "port")]: "8080" };
        expect(buildPayload(definition, values, data)).toEqual({});
    });

    it("leaves a value that is not a number for the server to reject", () => {
        const data = { ...untouched(), [formKey("cloud", "port")]: "abc" };
        expect(buildPayload(definition, values, data)).toEqual({ cloud: { port: "abc" } });
    });

    it("sends select values and multi-select lists, and clears an emptied list with null", () => {
        const data = { ...untouched(), [formKey("cloud", "region")]: "us", [formKey("cloud", "zones")]: ["a", "b"] };
        expect(buildPayload(definition, values, data)).toEqual({ cloud: { region: "us", zones: ["a", "b"] } });
        const emptied = { ...untouched(), [formKey("cloud", "zones")]: [] };
        expect(buildPayload(definition, values, emptied)).toEqual({ cloud: { zones: null } });
    });

    it("ignores inputs the form did not emit", () => {
        expect(buildPayload(definition, values, {})).toEqual({});
    });
});

describe("sections with defaults", () => {
    const two: ExtraPreferenceSection[] = [
        {
            name: "first",
            description: "First",
            inputs: [
                { name: "a", label: "A", type: "text", required: false, multiple: false, value: "def-a" },
                { name: "b", label: "B", type: "text", required: false, multiple: false, value: "def-b" },
            ],
        },
        {
            name: "second",
            description: "Second",
            inputs: [{ name: "c", label: "C", type: "text", required: false, multiple: false, value: "def-c" }],
        },
    ];
    const unset: ExtraPreferenceValues = { first: { a: null, b: null }, second: { c: null } };

    function form(edits: Record<string, unknown> = {}) {
        const data: Record<string, unknown> = {};
        for (const section of buildInputs(two, unset)) {
            for (const node of section.inputs ?? []) {
                data[formKey(section.name, node.name)] = node.value;
            }
        }
        return { ...data, ...edits } as Parameters<typeof buildPayload>[2];
    }

    it("is clean and sends nothing when no input was edited", () => {
        expect(dirtySections(two, unset, form()).size).toBe(0);
        expect(buildPayload(two, unset, form())).toEqual({});
    });

    it("sends only the edited section, including its defaults", () => {
        const data = form({ [formKey("first", "a")]: "mine" });
        expect([...dirtySections(two, unset, data)]).toEqual(["first"]);
        expect(buildPayload(two, unset, data)).toEqual({ first: { a: "mine", b: "def-b" } });
    });

    it("is clean again when an edit is reverted", () => {
        const data = form({ [formKey("first", "a")]: "def-a" });
        expect(dirtySections(two, unset, data).size).toBe(0);
        expect(buildPayload(two, unset, data)).toEqual({});
    });

    it("counts a typed secret as an edit and an empty one as none", () => {
        expect(dirtySections(definition, values, { [formKey("cloud", "token")]: "x" }).has("cloud")).toBe(true);
        expect(dirtySections(definition, values, { [formKey("cloud", "token")]: "" }).size).toBe(0);
    });
});

describe("secrets", () => {
    const edit = { [formKey("cloud", "endpoint")]: "https://other.example.org" };

    it("flags a required secret that is unset and left empty, in an edited section", () => {
        expect(isRequiredMissing(definition, values, { ...edit, [formKey("cloud", "api_key")]: "" })).toBe(true);
        expect(isRequiredMissing(definition, values, { ...edit, [formKey("cloud", "api_key")]: "x" })).toBe(false);
    });

    it("does not flag a stored required secret", () => {
        const stored = { cloud: { ...values.cloud!, api_key: { is_set: true } } };
        expect(isRequiredMissing(definition, stored, { ...edit, [formKey("cloud", "api_key")]: "" })).toBe(false);
    });

    it("flags any other required input that is left empty in an edited section", () => {
        const data = { ...edit, [formKey("cloud", "api_key")]: "x" };
        expect(isRequiredMissing(definition, values, data)).toBe(false);
        expect(isRequiredMissing(definition, values, { ...data, [formKey("cloud", "endpoint")]: "" })).toBe(true);
    });

    it("names the missing required inputs of edited sections only", () => {
        const data = { ...edit, [formKey("cloud", "endpoint")]: "", [formKey("cloud", "api_key")]: "" };
        expect(missingRequiredInputs(definition, values, data)).toEqual([
            formKey("cloud", "endpoint"),
            formKey("cloud", "api_key"),
        ]);
        expect(missingRequiredInputs(definition, values, untouched())).toEqual([]);
    });

    it("never flags a section the user did not edit", () => {
        expect(isRequiredMissing(definition, values, untouched())).toBe(false);
        expect(isRequiredMissing(definition, values, { [formKey("cloud", "api_key")]: "" })).toBe(false);
    });

    it("lists stored optional secrets as clearable, never required ones", () => {
        expect(clearableSecrets(definition, values)).toEqual([
            { section: "cloud", sectionLabel: "Cloud storage", name: "token", label: "Token" },
        ]);
        const stored = { cloud: { ...values.cloud!, api_key: { is_set: true } } };
        expect(clearableSecrets(definition, stored).map((s) => s.name)).toEqual(["token"]);
    });

    it("clears one secret with null", () => {
        expect(buildClearPayload("cloud", "token")).toEqual({ cloud: { token: null } });
    });
});
