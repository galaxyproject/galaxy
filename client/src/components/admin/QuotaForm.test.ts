import "@/composables/__mocks__/filter";

import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { components } from "@/api";
import { useServerMock } from "@/api/client/__mocks__";
import { resetMockConfig, setMockConfig } from "@/composables/__mocks__/config";

import QuotaForm from "./QuotaForm.vue";
import FormSelection from "@/components/Form/Elements/FormSelection.vue";

type QuotaDetails = components["schemas"]["QuotaDetails"];

vi.mock("@/composables/config");

const mockPush = vi.fn();

vi.mock("vue-router", () => ({
    useRouter: () => ({
        push: (...args: unknown[]) => mockPush(...args),
    }),
}));

const { server, http } = useServerMock();

const SELECTORS = {
    NAME: "#admin-quota-name",
    DESCRIPTION: "#admin-quota-description",
    AMOUNT: "#admin-quota-amount",
    USERS: "#admin-quota-users",
    GROUPS: "#admin-quota-groups",
    SOURCE_LABEL: "#admin-quota-source-label",
    SUBMIT: "#admin-quota-submit",
};

function quotaDetails(overrides: Partial<QuotaDetails> = {}): QuotaDetails {
    return {
        id: "q1",
        model_class: "Quota",
        name: "Existing Quota",
        description: "Existing Description",
        bytes: 1234567890,
        operation: "=",
        display_amount: "1.2 GB",
        default: [],
        users: [
            {
                model_class: "UserQuotaAssociation",
                user: {
                    id: "u1",
                    email: "user1@example.org",
                    username: "user1",
                    active: true,
                    deleted: false,
                    last_password_change: null,
                    model_class: "User",
                },
            },
        ],
        groups: [
            {
                model_class: "GroupQuotaAssociation",
                group: { id: "g1", name: "Group 1", model_class: "Group" },
            },
        ],
        ...overrides,
    };
}

/** Records the bodies of quota updates (PUT) and creations (POST). */
function captureRequests() {
    const requests: { put: unknown[]; post: unknown[] } = { put: [], post: [] };
    server.use(
        http.put("/api/quotas/{id}", async ({ request, response }) => {
            requests.put.push(await request.json());
            return response(200).json("");
        }),
        http.post("/api/quotas", async ({ request, response }) => {
            requests.post.push(await request.json());
            return response(200).json({
                id: "q2",
                model_class: "Quota",
                name: "New Quota",
                url: "/api/quotas/q2",
                message: "",
                quota_source_label: null,
            });
        }),
    );
    return requests;
}

async function mountQuotaForm(quotaId?: string) {
    const wrapper = mount(QuotaForm, {
        global: getLocalVue(),
        props: { quotaId },
    });
    await flushPromises();
    return wrapper;
}

async function mountEditForm(quota: QuotaDetails) {
    server.use(http.get("/api/quotas/{id}", ({ response }) => response(200).json(quota)));
    return mountQuotaForm(quota.id);
}

async function choose(wrapper: VueWrapper, selectionId: string, value: string) {
    const selection = wrapper.findAllComponents(FormSelection).find((w) => w.attributes("id") === selectionId);
    if (!selection) {
        throw new Error(`No FormSelection with id "${selectionId}".`);
    }
    selection.vm.$emit("input", value);
    await flushPromises();
}

async function submit(wrapper: VueWrapper) {
    await wrapper.find(SELECTORS.SUBMIT).trigger("click");
    await flushPromises();
}

beforeEach(() => {
    resetMockConfig();
    mockPush.mockClear();
    server.use(
        http.get("/api/groups", ({ response }) =>
            response(200).json([{ id: "g1", name: "Group 1", url: "/api/groups/g1", model_class: "Group" }]),
        ),
    );
});

describe("QuotaForm.vue edit mode", () => {
    it("loads all quota fields", async () => {
        const wrapper = await mountEditForm(quotaDetails());

        expect(wrapper.find(SELECTORS.NAME).element).toHaveValue("Existing Quota");
        expect(wrapper.find(SELECTORS.DESCRIPTION).element).toHaveValue("Existing Description");
        expect(wrapper.find(SELECTORS.AMOUNT).element).toHaveValue("1.2 GB");
    });

    it("keeps the saved name in the title while the name is edited", async () => {
        const wrapper = await mountEditForm(quotaDetails());

        await wrapper.find(SELECTORS.NAME).setValue("Renamed Quota");

        expect(wrapper.text()).toContain("Quota 'Existing Quota'");
        expect(wrapper.text()).not.toContain("Quota 'Renamed Quota'");
    });

    it("does not send the rounded amount back when it was not changed", async () => {
        const requests = captureRequests();
        const wrapper = await mountEditForm(quotaDetails());

        await wrapper.find(SELECTORS.NAME).setValue("Renamed Quota");
        await submit(wrapper);

        expect(requests.put).toEqual([
            {
                name: "Renamed Quota",
                description: "Existing Description",
                operation: "=",
                in_users: ["u1"],
                in_groups: ["g1"],
            },
        ]);
        expect(mockPush).toHaveBeenCalledWith("/admin/quotas");
    });

    it("sends a changed amount with its operation", async () => {
        const requests = captureRequests();
        const wrapper = await mountEditForm(quotaDetails());

        await wrapper.find(SELECTORS.AMOUNT).setValue("2 GB");
        await submit(wrapper);

        expect(requests.put).toMatchObject([{ amount: "2 GB", operation: "=" }]);
    });

    it("sends the amount along with a changed operation", async () => {
        const requests = captureRequests();
        const wrapper = await mountEditForm(quotaDetails());

        await choose(wrapper, "admin-quota-operation", "+");
        await submit(wrapper);

        expect(requests.put).toMatchObject([{ amount: "1.2 GB", operation: "+" }]);
    });

    it("drops users and groups when the quota becomes a default", async () => {
        const requests = captureRequests();
        const wrapper = await mountEditForm(quotaDetails());

        await choose(wrapper, "admin-quota-default", "registered");
        expect(wrapper.find(SELECTORS.USERS).exists()).toBe(false);
        await submit(wrapper);

        expect(requests.put).toEqual([
            {
                name: "Existing Quota",
                description: "Existing Description",
                operation: "=",
                default: "registered",
            },
        ]);
    });

    it("leaves an existing default quota's default and associations alone", async () => {
        const requests = captureRequests();
        const wrapper = await mountEditForm(
            quotaDetails({
                default: [{ model_class: "DefaultQuotaAssociation", type: "registered" }],
                users: [],
                groups: [],
            }),
        );

        expect(wrapper.find(SELECTORS.USERS).exists()).toBe(false);
        expect(wrapper.find(SELECTORS.GROUPS).exists()).toBe(false);
        await submit(wrapper);

        expect(requests.put).toEqual([{ name: "Existing Quota", description: "Existing Description", operation: "=" }]);
    });

    it("saves without a description", async () => {
        const requests = captureRequests();
        const wrapper = await mountEditForm(quotaDetails());

        await wrapper.find(SELECTORS.DESCRIPTION).setValue("");
        await submit(wrapper);

        expect(requests.put).toMatchObject([{ description: "" }]);
    });

    it("requires a name and an amount", async () => {
        const requests = captureRequests();
        const wrapper = await mountEditForm(quotaDetails());

        await wrapper.find(SELECTORS.AMOUNT).setValue("");
        await submit(wrapper);

        expect(wrapper.text()).toContain("Please enter a name and amount.");
        expect(requests.put).toEqual([]);
    });

    it("cannot be saved when the quota fails to load", async () => {
        server.use(
            http.get("/api/quotas/{id}", ({ response }) =>
                response("4XX").json({ err_msg: "Quota not found", err_code: 404 }, { status: 404 }),
            ),
        );

        const wrapper = await mountQuotaForm("q1");

        expect(wrapper.text()).toContain("Quota not found");
        expect(wrapper.find(SELECTORS.SUBMIT).exists()).toBe(false);
    });
});

describe("QuotaForm.vue create mode", () => {
    async function fillRequiredFields(wrapper: VueWrapper) {
        await wrapper.find(SELECTORS.NAME).setValue("New Quota");
        await wrapper.find(SELECTORS.DESCRIPTION).setValue("New Description");
        await wrapper.find(SELECTORS.AMOUNT).setValue("10 GB");
    }

    it("creates a quota for a labeled object store", async () => {
        setMockConfig({ quota_source_labels: ["mylabel"] });
        const requests = captureRequests();
        const wrapper = await mountQuotaForm();

        await fillRequiredFields(wrapper);
        await choose(wrapper, "admin-quota-source-label", "mylabel");
        await submit(wrapper);

        expect(requests.post).toEqual([
            {
                name: "New Quota",
                description: "New Description",
                amount: "10 GB",
                operation: "=",
                default: "no",
                quota_source_label: "mylabel",
                in_users: [],
                in_groups: [],
            },
        ]);
        expect(mockPush).toHaveBeenCalledWith("/admin/quotas");
    });

    it("creates a quota for the default object store", async () => {
        setMockConfig({ quota_source_labels: ["mylabel"] });
        const requests = captureRequests();
        const wrapper = await mountQuotaForm();

        await fillRequiredFields(wrapper);
        await submit(wrapper);

        expect(requests.post).toMatchObject([{ quota_source_label: null }]);
    });

    it("hides the object store choice when there are no labeled object stores", async () => {
        const wrapper = await mountQuotaForm();

        expect(wrapper.find(SELECTORS.SOURCE_LABEL).exists()).toBe(false);
    });

    it("requires a description", async () => {
        const requests = captureRequests();
        const wrapper = await mountQuotaForm();

        await wrapper.find(SELECTORS.NAME).setValue("New Quota");
        await wrapper.find(SELECTORS.AMOUNT).setValue("10 GB");
        await submit(wrapper);

        expect(wrapper.text()).toContain("Please enter a name, description and amount.");
        expect(requests.post).toEqual([]);
    });
});
