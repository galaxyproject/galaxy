import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
import { deferred } from "@tests/vitest/deferred";
import { createTestRouter, getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { reactive } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type { WorkflowSummary } from "@/api/workflows";
import { updateWorkflow } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";

import { generateRandomWorkflow } from "../testUtils";

import WorkflowCard from "./WorkflowCard.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";

vi.mock("@/components/Workflow/workflows.services", () => ({
    updateWorkflow: vi.fn(),
}));

vi.mock("@/composables/toast");

const mockedUpdateWorkflow = vi.mocked(updateWorkflow);

const { server, http } = useServerMock();

const OWNER = "fake_username";

function mountWorkflowCard() {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    useUserStore().currentUser = getFakeRegisteredUser({ username: OWNER });

    // reactive like the entries of the workflow list
    const workflow = reactive({
        ...generateRandomWorkflow(OWNER),
        tags: [],
        deleted: false,
    }) as unknown as WorkflowSummary;
    const wrapper = mount(WorkflowCard as object, {
        props: { workflow },
        global: getLocalVue(),
        pinia,
        router: createTestRouter(),
    });
    return { wrapper, workflow };
}

/** Adds a tag the way the tag editor does: to the tags the card currently shows. */
async function addTag(wrapper: ReturnType<typeof mount>, tag: string) {
    const editor = wrapper.findComponent(StatelessTags);
    editor.vm.$emit("input", [...(editor.props("value") as string[]), tag]);
    await wrapper.vm.$nextTick();
}

describe("WorkflowCard", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockedUpdateWorkflow.mockReset();
        server.use(
            http.get("/api/workflows/{workflow_id}/counts", ({ response }) => {
                return response(200).json({});
            }),
        );
    });

    it("reloads the list when a tag save fails", async () => {
        mockedUpdateWorkflow.mockRejectedValueOnce(new Error("save failed"));
        const { wrapper } = mountWorkflowCard();

        await addTag(wrapper, "first");
        await flushPromises();

        expect(Toast.error).toHaveBeenCalledTimes(1);
        expect(wrapper.emitted("refreshList")).toEqual([[true, true]]);
    });

    it("shows the saved tags again when a list reload during the save brought back older ones", async () => {
        const save = deferred();
        mockedUpdateWorkflow.mockImplementationOnce(() => save.promise as never);
        const { wrapper, workflow } = mountWorkflowCard();

        await addTag(wrapper, "first");
        // the list was reloaded before the save reached the server
        const reloadedWorkflow = reactive({ ...workflow, tags: [] as string[] }) as unknown as WorkflowSummary;
        await wrapper.setProps({ workflow: reloadedWorkflow } as object);
        expect(wrapper.findComponent(StatelessTags).props("value")).toEqual([]);

        save.resolve({ tags: ["first"] });
        await flushPromises();

        expect(mockedUpdateWorkflow).toHaveBeenCalledWith(workflow.id, { tags: ["first"] });
        expect(reloadedWorkflow.tags).toEqual(["first"]);
        expect(wrapper.findComponent(StatelessTags).props("value")).toEqual(["first"]);
        expect(wrapper.emitted("refreshList")).toBeUndefined();
    });

    it("shows the tags as the server stored them", async () => {
        mockedUpdateWorkflow.mockResolvedValueOnce({ tags: ["group:liver"] } as WorkflowSummary);
        const { wrapper, workflow } = mountWorkflowCard();

        await addTag(wrapper, "group=liver");
        await flushPromises();

        expect(mockedUpdateWorkflow).toHaveBeenCalledWith(workflow.id, { tags: ["group=liver"] });
        expect(wrapper.findComponent(StatelessTags).props("value")).toEqual(["group:liver"]);
        expect(wrapper.emitted("refreshList")).toBeUndefined();
    });
});
