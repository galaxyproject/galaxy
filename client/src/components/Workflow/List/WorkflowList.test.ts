import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, suppressBootstrapVueWarnings } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import VueRouter from "vue-router";

import { loadWorkflows } from "@/api/workflows";
import { useUserStore } from "@/stores/userStore";

import { generateRandomWorkflowList } from "../testUtils";

import WorkflowList from "./WorkflowList.vue";

vi.mock("@/api/workflows", () => ({
    loadWorkflows: vi.fn(),
}));

const mockedLoadWorkflows = loadWorkflows as ReturnType<typeof vi.fn>;

const localVue = getLocalVue();
localVue.use(VueRouter);
const router = new VueRouter();

const FAKE_USER_ID = "fake_user_id";
const FAKE_USERNAME = "fake_username";
const FAKE_USER_EMAIL = "fake_user_email";
const FAKE_USER = getFakeRegisteredUser({
    id: FAKE_USER_ID,
    email: FAKE_USER_EMAIL,
    username: FAKE_USERNAME,
});

async function mountWorkflowList() {
    const pinia = createTestingPinia({ createSpy: vi.fn });
    setActivePinia(pinia);

    const wrapper = mount(WorkflowList as object, {
        localVue,
        pinia,
        router,
    });

    const userStore = useUserStore();
    userStore.currentUser = FAKE_USER;

    await flushPromises();

    return wrapper;
}

describe("WorkflowList", () => {
    beforeEach(() => {
        suppressBootstrapVueWarnings();
        vi.clearAllMocks();
    });

    it("render empty workflow list", async () => {
        mockedLoadWorkflows.mockResolvedValue({ data: [], totalMatches: 0 });
        const wrapper = await mountWorkflowList();

        expect(wrapper.findAll(".workflow-card")).toHaveLength(0);
        expect(wrapper.find("#workflow-list-empty").exists()).toBe(true);
    });

    it("render workflow list", async () => {
        const FAKE_WORKFLOWS = generateRandomWorkflowList(FAKE_USERNAME, 10);
        mockedLoadWorkflows.mockResolvedValue({ data: FAKE_WORKFLOWS, totalMatches: 10 });
        const wrapper = await mountWorkflowList();

        expect(wrapper.findAll(".workflow-card")).toHaveLength(10);
        expect(wrapper.find("#workflow-list-empty").exists()).toBe(false);

        const nonDeletedWorkflows = FAKE_WORKFLOWS.filter((w) => !w.deleted);
        expect(wrapper.findAll(".workflow-card")).toHaveLength(nonDeletedWorkflows.length);
    });

    it("toggle show deleted workflows", async () => {
        const FAKE_WORKFLOWS = generateRandomWorkflowList(FAKE_USERNAME, 10);
        FAKE_WORKFLOWS.forEach((w) => (w.deleted = true));
        mockedLoadWorkflows.mockResolvedValue({ data: FAKE_WORKFLOWS, totalMatches: 10 });
        const wrapper = await mountWorkflowList();

        expect((wrapper.find("#workflow-list-filter input").element as HTMLInputElement).value).toBe("");

        const showDeletedButton = wrapper.find("#show-deleted");
        expect(showDeletedButton.exists()).toBe(true);
        showDeletedButton.trigger("click");

        await wrapper.vm.$nextTick();

        expect((wrapper.find("#workflow-list-filter input").element as HTMLInputElement).value).toBe("is:deleted");

        expect(showDeletedButton.exists()).toBe(true);
        showDeletedButton.trigger("click");

        await wrapper.vm.$nextTick();

        expect((wrapper.find("#workflow-list-filter input").element as HTMLInputElement).value).toBe("");
        await flushPromises();
    });
});
