import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import type { components } from "@/api/schema";
import { useUserStore } from "@/stores/userStore";

import UserExtraPreferences from "./UserExtraPreferences.vue";
import FormSelection from "@/components/Form/Elements/FormSelection.vue";

const confirm = vi.fn();
vi.mock("@/composables/confirmDialog", () => ({
    useConfirmDialog: () => ({ confirm }),
}));

const localVue = getLocalVue();
const { server, http } = useServerMock();

type Definition = components["schemas"]["ExtraPreferenceSectionDefinition"][];
type Values = components["schemas"]["UserExtraPreferences"];

const DEFINITION: Definition = [
    {
        name: "cloud",
        description: "Cloud storage",
        inputs: [
            { name: "endpoint", label: "Endpoint", type: "text", required: false, multiple: false },
            { name: "token", label: "Token", type: "secret", required: false, store: "vault", multiple: false },
            { name: "api_key", label: "API key", type: "password", required: true, multiple: false },
            { name: "port", label: "Port", type: "integer", required: false, multiple: false },
            { name: "verify", label: "Verify TLS", type: "boolean", required: false, multiple: false },
        ],
    },
];

const VALUES: Values = {
    cloud: {
        endpoint: "https://example.org",
        token: { is_set: true },
        api_key: { is_set: false },
        port: null,
        verify: false,
    },
};

const putBodies: unknown[] = [];

function serve(definition: Definition = DEFINITION, values: Values = VALUES, putStatus = 200) {
    putBodies.length = 0;
    server.use(
        http.get("/api/configuration/extra_preferences", ({ response }) => response(200).json(definition)),
        http.get("/api/users/{user_id}/extra_preferences", ({ response }) => response(200).json(values)),
        http.put("/api/users/{user_id}/extra_preferences", async ({ request, response }) => {
            const body = (await request.json()) as Record<string, Record<string, unknown>>;
            putBodies.push(body);
            if (putStatus !== 200) {
                return response("4XX").json(
                    { err_code: 400001, err_msg: "'API key' in 'Cloud storage' is required." },
                    {
                        status: 400,
                    },
                );
            }
            // the server answers with the values it stored; secrets only report that they are set
            const stored: Values = JSON.parse(JSON.stringify(values));
            for (const [section, inputs] of Object.entries(body)) {
                for (const [name, value] of Object.entries(inputs)) {
                    const sensitive = ["token", "api_key"].includes(name);
                    stored[section]![name] = sensitive ? { is_set: value !== null } : (value as never);
                }
            }
            return response(200).json(stored);
        }),
    );
}

async function mountPage() {
    const wrapper = mount(UserExtraPreferences as object, { global: localVue, pinia: createPinia() });
    useUserStore().currentUser = getFakeRegisteredUser({ id: "user1" });
    await flushPromises();
    return wrapper;
}

const field = (wrapper: VueWrapper, name: string) =>
    wrapper.find(`[id='cloud|${name}']`).element.tagName === "INPUT"
        ? wrapper.find(`[id='cloud|${name}']`)
        : wrapper.find(`[id='form-element-cloud|${name}'] input`);
const saveButton = (wrapper: VueWrapper) => wrapper.find("#save-extra-preferences");
const saveDisabled = (wrapper: VueWrapper) => saveButton(wrapper).attributes("aria-disabled") === "true";

async function save(wrapper: VueWrapper) {
    await saveButton(wrapper).trigger("click");
    await flushPromises();
}

describe("UserExtraPreferences", () => {
    beforeEach(() => {
        confirm.mockReset();
    });

    it("renders the sections and inputs of the definition with the stored values", async () => {
        serve();
        const wrapper = await mountPage();
        expect(wrapper.text()).toContain("Cloud storage");
        expect((field(wrapper, "endpoint").element as HTMLInputElement).value).toBe("https://example.org");
        expect(field(wrapper, "token").attributes("type")).toBe("password");
    });

    it("shows a stored secret as an empty field with a hint, never a placeholder value", async () => {
        serve();
        const wrapper = await mountPage();
        expect((field(wrapper, "token").element as HTMLInputElement).value).toBe("");
        expect(wrapper.text()).toContain("A value is stored");
        expect(wrapper.html()).not.toContain("__SECRET_PLACEHOLDER__");
    });

    it("says so when no extra configurations are defined", async () => {
        serve([], {});
        const wrapper = await mountPage();
        expect(wrapper.text()).toContain("No extra configurations are defined");
        expect(saveButton(wrapper).exists()).toBe(false);
    });

    it("shows the server message when loading fails", async () => {
        server.use(
            http.get("/api/configuration/extra_preferences", ({ response }) =>
                response("4XX").json({ err_code: 403002, err_msg: "Not allowed." }, { status: 403 }),
            ),
            http.get("/api/users/{user_id}/extra_preferences", ({ response }) => response(200).json(VALUES)),
        );
        const wrapper = await mountPage();
        expect(wrapper.text()).toContain("Not allowed.");
    });

    it("keeps Save disabled until something changes", async () => {
        serve(DEFINITION, { cloud: { ...VALUES.cloud!, api_key: { is_set: true } } });
        const wrapper = await mountPage();
        expect(saveDisabled(wrapper)).toBe(true);
        await field(wrapper, "endpoint").setValue("https://other.example.org");
        await flushPromises();
        expect(saveDisabled(wrapper)).toBe(false);
    });

    it("sends only the changed input and shows the success message", async () => {
        serve();
        const wrapper = await mountPage();
        await field(wrapper, "endpoint").setValue("https://other.example.org");
        await field(wrapper, "api_key").setValue("key");
        await flushPromises();
        await save(wrapper);
        expect(putBodies).toEqual([{ cloud: { endpoint: "https://other.example.org", api_key: "key" } }]);
        expect(wrapper.text()).toContain("Extra configurations saved");
    });

    it("sends a number as a number", async () => {
        serve();
        const wrapper = await mountPage();
        await field(wrapper, "port").setValue("9090");
        await flushPromises();
        await field(wrapper, "api_key").setValue("key");
        await flushPromises();
        await save(wrapper);
        expect(putBodies).toEqual([{ cloud: { port: 9090, api_key: "key" } }]);
    });

    it("sends an emptied optional input as null", async () => {
        serve();
        const wrapper = await mountPage();
        await field(wrapper, "endpoint").setValue("");
        await field(wrapper, "api_key").setValue("key");
        await flushPromises();
        await save(wrapper);
        expect(putBodies).toEqual([{ cloud: { endpoint: null, api_key: "key" } }]);
    });

    it("empties a secret field after saving it", async () => {
        serve();
        const wrapper = await mountPage();
        await field(wrapper, "token").setValue("s3cret");
        await field(wrapper, "api_key").setValue("key");
        await flushPromises();
        await save(wrapper);
        expect(putBodies).toEqual([{ cloud: { token: "s3cret", api_key: "key" } }]);
        expect((field(wrapper, "token").element as HTMLInputElement).value).toBe("");
        expect((field(wrapper, "api_key").element as HTMLInputElement).value).toBe("");
    });

    it("blocks Save while a required secret is unset", async () => {
        serve();
        const wrapper = await mountPage();
        await field(wrapper, "endpoint").setValue("https://other.example.org");
        await flushPromises();
        expect(saveDisabled(wrapper)).toBe(true);
        await field(wrapper, "api_key").setValue("key");
        await flushPromises();
        expect(saveDisabled(wrapper)).toBe(false);
    });

    it("does not block Save on a required secret that is stored", async () => {
        serve(DEFINITION, { cloud: { ...VALUES.cloud!, api_key: { is_set: true } } });
        const wrapper = await mountPage();
        await field(wrapper, "endpoint").setValue("https://other.example.org");
        await flushPromises();
        expect(saveDisabled(wrapper)).toBe(false);
        await save(wrapper);
        expect(putBodies).toEqual([{ cloud: { endpoint: "https://other.example.org" } }]);
    });

    it("removes a stored optional secret after confirmation, and offers no removal for required ones", async () => {
        serve(DEFINITION, { cloud: { ...VALUES.cloud!, api_key: { is_set: true } } });
        confirm.mockResolvedValue(true);
        const wrapper = await mountPage();
        expect(wrapper.find("[data-description='clear cloud|api_key']").exists()).toBe(false);
        await wrapper.find("[data-description='clear cloud|token']").trigger("click");
        await flushPromises();
        expect(putBodies).toEqual([{ cloud: { token: null } }]);
        expect(wrapper.find("[data-description='clear cloud|token']").exists()).toBe(false);
    });

    it("keeps a stored secret when the removal is not confirmed", async () => {
        serve();
        confirm.mockResolvedValue(false);
        const wrapper = await mountPage();
        await wrapper.find("[data-description='clear cloud|token']").trigger("click");
        await flushPromises();
        expect(putBodies).toEqual([]);
    });

    it("shows the server message when saving fails and keeps what was typed", async () => {
        serve(DEFINITION, VALUES, 400);
        const wrapper = await mountPage();
        await field(wrapper, "endpoint").setValue("https://other.example.org");
        await field(wrapper, "api_key").setValue("key");
        await flushPromises();
        await save(wrapper);
        expect(wrapper.text()).toContain("is required.");
        expect((field(wrapper, "endpoint").element as HTMLInputElement).value).toBe("https://other.example.org");
    });

    it("names the section on the removal button", async () => {
        serve();
        const wrapper = await mountPage();
        expect(wrapper.find("[data-description='clear cloud|token']").text()).toContain("Cloud storage");
    });

    it("reloads the page after saving a section the app reads at startup", async () => {
        const reload = vi.fn();
        vi.stubGlobal("location", { ...window.location, reload });
        try {
            serve(
                [
                    {
                        name: "localization",
                        description: "Language",
                        inputs: [{ name: "locale", label: "Locale", type: "text", required: false, multiple: false }],
                    },
                ],
                { localization: { locale: null } },
            );
            const wrapper = await mountPage();
            await wrapper.find("[id='localization|locale']").setValue("de");
            await flushPromises();
            await save(wrapper);
            expect(putBodies).toEqual([{ localization: { locale: "de" } }]);
            expect(reload).toHaveBeenCalledOnce();
        } finally {
            vi.unstubAllGlobals();
        }
    });

    it("does not reload after saving another section", async () => {
        const reload = vi.fn();
        vi.stubGlobal("location", { ...window.location, reload });
        try {
            serve(DEFINITION, { cloud: { ...VALUES.cloud!, api_key: { is_set: true } } });
            const wrapper = await mountPage();
            await field(wrapper, "endpoint").setValue("https://other.example.org");
            await flushPromises();
            await save(wrapper);
            expect(reload).not.toHaveBeenCalled();
        } finally {
            vi.unstubAllGlobals();
        }
    });
});

describe("UserExtraPreferences with every input type", () => {
    const TYPED: Definition = [
        {
            name: "typed",
            description: "Typed section",
            inputs: [
                {
                    name: "needed",
                    label: "Needed",
                    type: "select",
                    required: true,
                    multiple: false,
                    options: [
                        ["First", "first"],
                        ["Second", "second"],
                    ],
                },
                {
                    name: "region",
                    label: "Region",
                    required: false,
                    multiple: false,
                    options: [
                        ["EU", "eu"],
                        ["US", "us"],
                    ],
                },
                {
                    name: "zones",
                    label: "Zones",
                    type: "select",
                    required: false,
                    multiple: true,
                    options: [
                        ["A", "a"],
                        ["B", "b"],
                    ],
                },
                { name: "verify", label: "Verify", type: "boolean", required: false, multiple: false },
                { name: "title", label: "Title", type: "text", required: true, multiple: false },
            ],
        },
    ];
    const UNSET: Values = { typed: { needed: null, region: null, zones: null, verify: null, title: null } };

    beforeEach(() => {
        confirm.mockReset();
    });

    it("does not pick or send anything on its own", async () => {
        serve(TYPED, UNSET);
        const wrapper = await mountPage();
        expect(saveDisabled(wrapper)).toBe(true);
        expect(putBodies).toEqual([]);
    });

    it("blocks Save while a required input that was never set is empty, in any section", async () => {
        serve(TYPED, UNSET);
        const wrapper = await mountPage();
        await wrapper.find("[id='form-element-typed|verify'] input").setValue(true);
        await flushPromises();
        expect(saveDisabled(wrapper)).toBe(true);
    });

    it("sends select, multi-select and boolean values once the required inputs are filled", async () => {
        serve(TYPED, UNSET);
        const wrapper = await mountPage();
        await wrapper.find("[id='typed|title']").setValue("A title");
        await wrapper.find("[id='form-element-typed|verify'] input").setValue(true);
        const selections = wrapper.findAllComponents(FormSelection);
        expect(selections).toHaveLength(3);
        // the widgets are given their value the way their own change handler does
        selections[0]!.vm.$emit("update:modelValue", "second");
        selections[1]!.vm.$emit("update:modelValue", "us");
        selections[2]!.vm.$emit("update:modelValue", ["a", "b"]);
        await flushPromises();
        expect(saveDisabled(wrapper)).toBe(false);
        await save(wrapper);
        expect(putBodies).toEqual([
            { typed: { needed: "second", region: "us", zones: ["a", "b"], verify: true, title: "A title" } },
        ]);
    });
});
