import "@/composables/__mocks__/filter";

import { composeStories } from "@storybook/vue3-vite";
import { createTestRouter } from "@tests/vitest/helpers";
import { type StoryOf, useStoryMount } from "@tests/vitest/stories";
import type { VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { useConfigStore } from "@/stores/configurationStore";

import * as QuotaFormStories from "./QuotaForm.stories";
import { ADMIN_GROUPS, ADMIN_USER } from "./test_fixtures";

import FormSelection from "@/components/Form/Elements/FormSelection.vue";

const stories = composeStories(QuotaFormStories);
const mountStory = useStoryMount();
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

// The quota ExistingQuota loads, with ADMIN_USER and the first of ADMIN_GROUPS.
const QUOTA_NAME = "Workshop participants";
const QUOTA_DESCRIPTION = "Extra space for the RNA-seq workshop";
const QUOTA_AMOUNT = "1.2 GB";
const QUOTA_GROUP_ID = ADMIN_GROUPS[0]!.id;
// The quota label NewQuotaForLabeledStorage's Galaxy offers.
const STORAGE_LABEL = "scratch";

/** Records the bodies of quota updates (PUT) and creations (POST); the story still answers. */
function captureRequests() {
    const requests: { put: unknown[]; post: unknown[] } = { put: [], post: [] };
    server.use(
        http.put("/api/quotas/{id}", async ({ request }) => {
            requests.put.push(await request.clone().json());
        }),
        http.post("/api/quotas", async ({ request }) => {
            requests.post.push(await request.clone().json());
        }),
    );
    return requests;
}

/** Mounts the story on its form page, so leaving it for the quotas list is observable. */
async function mountQuotaForm(story: StoryOf<typeof stories>) {
    const router = createTestRouter();
    const formPage = story.args.quotaId ? "/admin/form/edit_quota" : "/admin/form/create_quota";
    await router.push(formPage);
    const wrapper = mountStory(story, { router });
    await vi.waitFor(() => expect(useConfigStore().isLoaded).toBe(true));
    await flushPromises();
    return { wrapper, router, formPage, requests: captureRequests() };
}

async function choose(wrapper: VueWrapper, selectionId: string, value: string) {
    const selection = wrapper.findAllComponents(FormSelection).find((w) => w.props("id") === selectionId);
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

describe("QuotaForm.vue edit mode", () => {
    it("loads all quota fields", async () => {
        const { wrapper } = await mountQuotaForm(stories.ExistingQuota);

        expect(wrapper.find(SELECTORS.NAME).element).toHaveValue(QUOTA_NAME);
        expect(wrapper.find(SELECTORS.DESCRIPTION).element).toHaveValue(QUOTA_DESCRIPTION);
        expect(wrapper.find(SELECTORS.AMOUNT).element).toHaveValue(QUOTA_AMOUNT);
    });

    it("keeps the saved name in the title while the name is edited", async () => {
        const { wrapper } = await mountQuotaForm(stories.ExistingQuota);

        await wrapper.find(SELECTORS.NAME).setValue("Renamed Quota");

        expect(wrapper.text()).toContain(`Quota '${QUOTA_NAME}'`);
        expect(wrapper.text()).not.toContain("Quota 'Renamed Quota'");
    });

    it("does not send the rounded amount back when it was not changed", async () => {
        const { wrapper, router, requests } = await mountQuotaForm(stories.ExistingQuota);

        await wrapper.find(SELECTORS.NAME).setValue("Renamed Quota");
        await submit(wrapper);

        expect(requests.put).toEqual([
            {
                name: "Renamed Quota",
                description: QUOTA_DESCRIPTION,
                operation: "=",
                in_users: [ADMIN_USER.id],
                in_groups: [QUOTA_GROUP_ID],
            },
        ]);
        expect(router.currentRoute.value.path).toBe("/admin/quotas");
    });

    it("sends a changed amount with its operation", async () => {
        const { wrapper, requests } = await mountQuotaForm(stories.ExistingQuota);

        await wrapper.find(SELECTORS.AMOUNT).setValue("2 GB");
        await submit(wrapper);

        expect(requests.put).toMatchObject([{ amount: "2 GB", operation: "=" }]);
    });

    it("sends the amount along with a changed operation", async () => {
        const { wrapper, requests } = await mountQuotaForm(stories.ExistingQuota);

        await choose(wrapper, "admin-quota-operation", "+");
        await submit(wrapper);

        expect(requests.put).toMatchObject([{ amount: QUOTA_AMOUNT, operation: "+" }]);
    });

    it("drops users and groups when the quota becomes a default", async () => {
        const { wrapper, requests } = await mountQuotaForm(stories.ExistingQuota);

        await choose(wrapper, "admin-quota-default", "registered");
        expect(wrapper.find(SELECTORS.USERS).exists()).toBe(false);
        await submit(wrapper);

        expect(requests.put).toEqual([
            {
                name: QUOTA_NAME,
                description: QUOTA_DESCRIPTION,
                operation: "=",
                default: "registered",
            },
        ]);
    });

    it("leaves an existing default quota's default and associations alone", async () => {
        const { wrapper, requests } = await mountQuotaForm(stories.ExistingDefaultQuota);

        expect(wrapper.find(SELECTORS.USERS).exists()).toBe(false);
        expect(wrapper.find(SELECTORS.GROUPS).exists()).toBe(false);
        await submit(wrapper);

        expect(requests.put).toEqual([{ name: QUOTA_NAME, description: QUOTA_DESCRIPTION, operation: "=" }]);
    });

    it("saves without a description", async () => {
        const { wrapper, requests } = await mountQuotaForm(stories.ExistingQuota);

        await wrapper.find(SELECTORS.DESCRIPTION).setValue("");
        await submit(wrapper);

        expect(requests.put).toMatchObject([{ description: "" }]);
    });

    it("requires a name and an amount", async () => {
        const { wrapper, router, formPage, requests } = await mountQuotaForm(stories.ExistingQuota);

        await wrapper.find(SELECTORS.AMOUNT).setValue("");
        await submit(wrapper);

        expect(wrapper.text()).toContain("Please enter a name and amount.");
        expect(requests.put).toEqual([]);
        expect(router.currentRoute.value.path).toBe(formPage);
    });

    it("cannot be saved when the quota fails to load", async () => {
        const { wrapper } = await mountQuotaForm(stories.ExistingQuotaDeleted);

        expect(wrapper.text()).toContain(`Quota "${QUOTA_NAME}" is deleted`);
        expect(wrapper.find(SELECTORS.SUBMIT).exists()).toBe(false);
    });
});

describe("QuotaForm.vue create mode", () => {
    async function fillRequiredFields(wrapper: VueWrapper) {
        await wrapper.find(SELECTORS.NAME).setValue("New Quota");
        await wrapper.find(SELECTORS.DESCRIPTION).setValue("New Description");
        await wrapper.find(SELECTORS.AMOUNT).setValue("10 GB");
    }

    it("associates the visible field labels with editable controls", async () => {
        const { wrapper } = await mountQuotaForm(stories.NewQuota);
        const ids = [
            "admin-quota-name",
            "admin-quota-description",
            "admin-quota-amount",
            "admin-quota-operation",
            "admin-quota-default",
            "admin-quota-groups-select",
            "admin-quota-users-select",
        ];
        for (const id of ids) {
            const label = wrapper.find(`label[for="${id}"]`);
            expect(label.exists(), `Label for ${id}`).toBe(true);
            expect(label.text().length).toBeGreaterThan(0);
            expect(wrapper.find(`input[id="${id}"]`).exists(), `Input for ${id}`).toBe(true);
        }
    });

    it("creates a quota for a labeled object store", async () => {
        const { wrapper, router, requests } = await mountQuotaForm(stories.NewQuotaForLabeledStorage);

        await fillRequiredFields(wrapper);
        await choose(wrapper, "admin-quota-source-label", STORAGE_LABEL);
        await submit(wrapper);

        expect(requests.post).toEqual([
            {
                name: "New Quota",
                description: "New Description",
                amount: "10 GB",
                operation: "=",
                default: "no",
                quota_source_label: STORAGE_LABEL,
                in_users: [],
                in_groups: [],
            },
        ]);
        expect(router.currentRoute.value.path).toBe("/admin/quotas");
    });

    it("creates a quota for the default object store", async () => {
        const { wrapper, requests } = await mountQuotaForm(stories.NewQuotaForLabeledStorage);

        expect(wrapper.find(SELECTORS.SOURCE_LABEL).exists()).toBe(true);
        await fillRequiredFields(wrapper);
        await submit(wrapper);

        expect(requests.post).toMatchObject([{ quota_source_label: null }]);
    });

    it("hides the object store choice when there are no labeled object stores", async () => {
        const { wrapper } = await mountQuotaForm(stories.NewQuota);

        expect(wrapper.find(SELECTORS.NAME).exists()).toBe(true);
        expect(wrapper.find(SELECTORS.SOURCE_LABEL).exists()).toBe(false);
    });

    it("requires a description", async () => {
        const { wrapper, router, formPage, requests } = await mountQuotaForm(stories.NewQuota);

        await wrapper.find(SELECTORS.NAME).setValue("New Quota");
        await wrapper.find(SELECTORS.AMOUNT).setValue("10 GB");
        await submit(wrapper);

        expect(wrapper.text()).toContain("Please enter a name, description and amount.");
        expect(requests.post).toEqual([]);
        expect(router.currentRoute.value.path).toBe(formPage);
    });
});
