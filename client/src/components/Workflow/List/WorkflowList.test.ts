import { createTestingPinia } from "@pinia/testing";
import { mount, shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { getLocalVue, injectTestRouter, suppressBootstrapVueWarnings } from "tests/jest/helpers";
import { getFakeRegisteredUser } from "tests/test-data";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import { generateRandomWorkflowList } from "../testUtils";

import WorkflowList from "./WorkflowList.vue";

const globalConfig = getLocalVue();
const router = injectTestRouter();

const { server, http } = useServerMock();

const FAKE_USER_ID = "fake_user_id";
const FAKE_USERNAME = "fake_username";
const FAKE_USER_EMAIL = "fake_user_email";
const FAKE_USER = getFakeRegisteredUser({
    id: FAKE_USER_ID,
    email: FAKE_USER_EMAIL,
    username: FAKE_USERNAME,
});

async function mountWorkflowList() {
    const pinia = createTestingPinia();
    setActivePinia(pinia);

    const wrapper = mount(WorkflowList as object, {
        props: {
            activeList: "published" // Avoid the "my" filtering logic that causes the error
        },
        global: {
            ...globalConfig.global,
            plugins: [...globalConfig.global.plugins, pinia, router],
            stubs: {
                'workflow-card': true,
                'workflow-card-list': true,
                'b-modal': true,
                'b-alert': true,
                'b-button': true,
                'b-nav': true,
                'b-nav-item': true,
                'b-overlay': true,
                'b-pagination': true,
                'stateless-tags': true,
                'tags-multiselect': true,
                'tags-selection-dialog': true,
                'filter-menu': true,
                'list-header': true,
                'heading': true,
                'breadcrumb-heading': true,
                'login-required': true,
                'loading-span': true,
                'workflow-list-actions': true,
                'g-link': true,
                'font-awesome-icon': true
            }
        },
    });

    const userStore = useUserStore();
    userStore.currentUser = FAKE_USER;

    await flushPromises();

    return wrapper;
}

describe("WorkflowList", () => {
    beforeEach(() => {
        server.use(
            http.get("/api/workflows/{workflow_id}/counts", ({ response }) => {
                return response(200).json({});
            }),
        );

        // The use of the tool tip in statelesstag without a real dom is causing issues
        suppressBootstrapVueWarnings();
    });

    it("render empty workflow list", async () => {
        server.use(
            http.get("/api/workflows", ({ response }) => {
                return response.untyped(HttpResponse.json({ data: [], totalMatches: 0 }));
            }),
        );

        const wrapper = await mountWorkflowList();

        expect(wrapper.findAll(".workflow-card")).toHaveLength(0);
        expect(wrapper.find("#workflow-list-empty").exists()).toBe(true);
    });

    it("render workflow list", async () => {
        const FAKE_WORKFLOWS = generateRandomWorkflowList(FAKE_USERNAME, 10);

        server.use(
            http.get("/api/workflows", ({ response }) => {
                // TODO: We use untyped here because the response is not yet defined in the schema
                return response.untyped(HttpResponse.json({ data: FAKE_WORKFLOWS, totalMatches: FAKE_WORKFLOWS.length }));
            }),
        );

        const wrapper = await mountWorkflowList();

        expect(wrapper.findAll(".workflow-card")).toHaveLength(10);
        expect(wrapper.find("#workflow-list-empty").exists()).toBe(false);

        const nonDeletedWorkflows = FAKE_WORKFLOWS.filter((w) => !w.deleted);
        expect(wrapper.findAll(".workflow-card")).toHaveLength(nonDeletedWorkflows.length);
    });

    it("toggle show deleted workflows", async () => {
        const FAKE_WORKFLOWS = generateRandomWorkflowList(FAKE_USERNAME, 10);
        FAKE_WORKFLOWS.forEach((w) => (w.deleted = true));

        server.use(
            http.get("/api/workflows", ({ response }) => {
                // TODO: We use untyped here because the response is not yet defined in the schema
                return response.untyped(HttpResponse.json({ data: FAKE_WORKFLOWS, totalMatches: FAKE_WORKFLOWS.length }));
            }),
        );

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
