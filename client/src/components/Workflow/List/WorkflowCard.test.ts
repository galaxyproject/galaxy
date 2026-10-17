import { createTestingPinia } from "@pinia/testing";
import { getFakeRegisteredUser } from "@tests/test-data";
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

function deferred() {
    let resolve!: (value: unknown) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
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

    it("saves tag edits one after another without reloading the list", async () => {
        const firstSave = deferred();
        const secondSave = deferred();
        mockedUpdateWorkflow
            .mockImplementationOnce(() => firstSave.promise as never)
            .mockImplementationOnce(() => secondSave.promise as never);
        const { wrapper, workflow } = mountWorkflowCard();

        await addTag(wrapper, "first");
        await addTag(wrapper, "second");

        expect(workflow.tags).toEqual(["first", "second"]);
        // the second save waits for the first, so an older tag list never lands last
        expect(mockedUpdateWorkflow).toHaveBeenCalledTimes(1);

        firstSave.resolve({});
        await flushPromises();
        expect(mockedUpdateWorkflow).toHaveBeenCalledTimes(2);
        expect(mockedUpdateWorkflow).toHaveBeenLastCalledWith(workflow.id, { tags: ["first", "second"] });

        secondSave.resolve({});
        await flushPromises();
        // a list reload would re-sort the list and move the card away from the open tag editor
        expect(wrapper.emitted("refreshList")).toBeUndefined();
    });

    it("reloads the list when a tag save fails", async () => {
        mockedUpdateWorkflow.mockRejectedValueOnce(new Error("save failed"));
        const { wrapper } = mountWorkflowCard();

        await addTag(wrapper, "first");
        await flushPromises();

        expect(Toast.error).toHaveBeenCalledTimes(1);
        expect(wrapper.emitted("refreshList")).toEqual([[true, true]]);
    });

    it("does not reload the list when a failed tag save is followed by a successful one", async () => {
        const firstSave = deferred();
        const secondSave = deferred();
        mockedUpdateWorkflow
            .mockImplementationOnce(() => firstSave.promise as never)
            .mockImplementationOnce(() => secondSave.promise as never);
        const { wrapper, workflow } = mountWorkflowCard();

        await addTag(wrapper, "first");
        await addTag(wrapper, "second");

        firstSave.reject(new Error("save failed"));
        await flushPromises();
        expect(Toast.error).toHaveBeenCalledTimes(1);
        // the queued save carries the newest tags, so a reload now could bring back the stored, older ones
        expect(wrapper.emitted("refreshList")).toBeUndefined();

        secondSave.resolve({});
        await flushPromises();
        expect(mockedUpdateWorkflow).toHaveBeenLastCalledWith(workflow.id, { tags: ["first", "second"] });
        expect(workflow.tags).toEqual(["first", "second"]);
        expect(wrapper.emitted("refreshList")).toBeUndefined();
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

        save.resolve({});
        await flushPromises();

        expect(reloadedWorkflow.tags).toEqual(["first"]);
        expect(wrapper.findComponent(StatelessTags).props("value")).toEqual(["first"]);
        expect(wrapper.emitted("refreshList")).toBeUndefined();
    });
});
