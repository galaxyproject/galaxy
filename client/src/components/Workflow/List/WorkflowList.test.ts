import { createTestingPinia } from "@pinia/testing";
import { getLocalVue } from "@tests/jest/helpers";
import { getFakeRegisteredUser } from "@tests/test-data";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import { useUserStore } from "@/stores/userStore";

import { generateRandomWorkflowList } from "../testUtils";

import WorkflowList from "./WorkflowList.vue";

const localVue = getLocalVue();

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

    const mockRouter = {
        push: jest.fn(),
        currentRoute: {
            query: {},
        },
    };

    const wrapper = mount(WorkflowList as object, {
        localVue,
        pinia,
        mocks: {
            $router: mockRouter,
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
            })
        );
    });

    it("render empty workflow list", async () => {
        server.use(
            http.get("/api/workflows", ({ response }) => {
                return response(200).json([]);
            })
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
                return response.untyped(HttpResponse.json(FAKE_WORKFLOWS));
            })
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
                return response.untyped(HttpResponse.json(FAKE_WORKFLOWS));
            })
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
    });
});
