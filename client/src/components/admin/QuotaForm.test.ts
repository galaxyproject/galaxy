import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { resetMockConfig, setMockConfig } from "@/composables/__mocks__/config";

import QuotaForm from "./QuotaForm.vue";
import FormSelection from "@/components/Form/Elements/FormSelection.vue";

vi.mock("@/composables/config");

const { server, http } = useServerMock();
const localVue = getLocalVue();
const mockPush = vi.fn();

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: (...args: unknown[]) => mockPush(...args),
    }),
}));

// FormSelection filters its options in a web worker, which the test environment does not provide.
vi.mock("@/composables/filter/filter.js", async () => {
    const { ref } = await import("vue");
    return {
        useFilterObjectArray: () => ({ filtered: ref([]), pending: ref(false) }),
    };
});

function quotaDetails(overrides: Record<string, unknown> = {}) {
    return {
        id: "q1",
        model_class: "Quota" as const,
        name: "Existing Quota",
        description: "Existing Description",
        bytes: 1234567890,
        operation: "=" as const,
        display_amount: "1.2 GB",
        default: [],
        users: [
            {
                model_class: "UserQuotaAssociation" as const,
                user: {
                    id: "u1",
                    email: "user1@example.org",
                    username: "user1",
                    active: true,
                    deleted: false,
                    last_password_change: null,
                    model_class: "User" as const,
                },
            },
        ],
        groups: [
            {
                model_class: "GroupQuotaAssociation" as const,
                group: { id: "g1", name: "Group 1", model_class: "Group" as const },
            },
        ],
        ...overrides,
    };
}

function useGroups() {
    server.use(
        http.get("/api/groups", ({ response }) =>
            response(200).json([{ id: "g1", name: "Group 1", url: "/api/groups/g1", model_class: "Group" }]),
        ),
    );
}

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

async function mountTarget(quota?: ReturnType<typeof quotaDetails>) {
    useGroups();
    if (quota) {
        server.use(http.get("/api/quotas/{id}", ({ response }) => response(200).json(quota)));
    }
    const wrapper = mount(QuotaForm as object, {
        localVue,
        propsData: quota ? { quotaId: quota.id } : {},
        stubs: { FontAwesomeIcon: true },
    });
    await flushPromises();
    return wrapper;
}

async function choose(wrapper: Wrapper<Vue>, selectionId: string, value: string) {
    const selection = wrapper.findAllComponents(FormSelection).wrappers.find((w) => w.attributes("id") === selectionId);
    selection!.vm.$emit("input", value);
    await flushPromises();
}

async function submit(wrapper: Wrapper<Vue>) {
    await wrapper.find("#admin-quota-submit").trigger("click");
    await flushPromises();
}

beforeEach(() => {
    // FormSelection reads a Pinia store.
    setActivePinia(createPinia());
    resetMockConfig();
    mockPush.mockClear();
});

describe("QuotaForm.vue edit mode", () => {
    it("loads all quota fields and titles the form with the saved name", async () => {
        const wrapper = await mountTarget(quotaDetails());
        expect(wrapper.find("#admin-quota-name").element).toHaveProperty("value", "Existing Quota");
        expect(wrapper.find("#admin-quota-description").element).toHaveProperty("value", "Existing Description");
        expect(wrapper.find("#admin-quota-amount").element).toHaveProperty("value", "1.2 GB");
        await wrapper.find("#admin-quota-name").setValue("Renamed Quota");
        expect(wrapper.text()).toContain("Quota 'Existing Quota'");
    });

    it("does not send the rounded amount back when it was not changed", async () => {
        const requests = captureRequests();
        const wrapper = await mountTarget(quotaDetails());
        await wrapper.find("#admin-quota-name").setValue("Renamed Quota");
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
        const wrapper = await mountTarget(quotaDetails());
        await wrapper.find("#admin-quota-amount").setValue("2 GB");
        await submit(wrapper);
        expect(requests.put).toMatchObject([{ amount: "2 GB", operation: "=" }]);
    });

    it("sends the amount along with a changed operation", async () => {
        const requests = captureRequests();
        const wrapper = await mountTarget(quotaDetails());
        await choose(wrapper, "admin-quota-operation", "+");
        await submit(wrapper);
        expect(requests.put).toMatchObject([{ amount: "1.2 GB", operation: "+" }]);
    });

    it("drops users and groups when the quota becomes a default", async () => {
        const requests = captureRequests();
        const wrapper = await mountTarget(quotaDetails());
        await choose(wrapper, "admin-quota-default", "registered");
        expect(wrapper.find("#admin-quota-users").exists()).toBe(false);
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
        const quota = quotaDetails({
            default: [{ model_class: "DefaultQuotaAssociation", type: "registered" }],
            users: [],
            groups: [],
        });
        const wrapper = await mountTarget(quota);
        expect(wrapper.find("#admin-quota-users").exists()).toBe(false);
        expect(wrapper.find("#admin-quota-groups").exists()).toBe(false);
        await submit(wrapper);
        expect(requests.put).toEqual([{ name: "Existing Quota", description: "Existing Description", operation: "=" }]);
    });

    it("saves without a description", async () => {
        const requests = captureRequests();
        const wrapper = await mountTarget(quotaDetails());
        await wrapper.find("#admin-quota-description").setValue("");
        await submit(wrapper);
        expect(requests.put).toMatchObject([{ description: "" }]);
    });

    it("requires a name and an amount", async () => {
        const requests = captureRequests();
        const wrapper = await mountTarget(quotaDetails());
        await wrapper.find("#admin-quota-amount").setValue("");
        await submit(wrapper);
        expect(wrapper.text()).toContain("Please enter a name and amount.");
        expect(requests.put).toEqual([]);
    });

    it("cannot be saved when the quota fails to load", async () => {
        useGroups();
        server.use(
            http.get("/api/quotas/{id}", ({ response }) =>
                response("4XX").json({ err_msg: "Quota not found", err_code: 404 }, { status: 404 }),
            ),
        );
        const wrapper = mount(QuotaForm as object, {
            localVue,
            propsData: { quotaId: "q1" },
            stubs: { FontAwesomeIcon: true },
        });
        await flushPromises();
        expect(wrapper.text()).toContain("Quota not found");
        expect(wrapper.find("#admin-quota-submit").exists()).toBe(false);
    });
});

describe("QuotaForm.vue create mode", () => {
    async function fillRequiredFields(wrapper: Wrapper<Vue>) {
        await wrapper.find("#admin-quota-name").setValue("New Quota");
        await wrapper.find("#admin-quota-description").setValue("New Description");
        await wrapper.find("#admin-quota-amount").setValue("10 GB");
    }

    it("creates a quota for a labeled object store", async () => {
        setMockConfig({ quota_source_labels: ["mylabel"] });
        const requests = captureRequests();
        const wrapper = await mountTarget();
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
        const wrapper = await mountTarget();
        await fillRequiredFields(wrapper);
        await submit(wrapper);
        expect(requests.post).toMatchObject([{ quota_source_label: null }]);
    });

    it("hides the object store choice when there are no labeled object stores", async () => {
        const wrapper = await mountTarget();
        expect(wrapper.find("#admin-quota-source-label").exists()).toBe(false);
    });

    it("requires a description", async () => {
        const requests = captureRequests();
        const wrapper = await mountTarget();
        await wrapper.find("#admin-quota-name").setValue("New Quota");
        await wrapper.find("#admin-quota-amount").setValue("10 GB");
        await submit(wrapper);
        expect(wrapper.text()).toContain("Please enter a name, description and amount.");
        expect(requests.post).toEqual([]);
    });
});
