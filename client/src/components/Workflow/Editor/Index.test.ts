import { createTestingPinia } from "@pinia/testing";
import {
    emittedArg,
    getLocalVue,
    mockUnprivilegedToolsRequest,
    suppressExpectedErrorMessages,
    withPlugins,
} from "@tests/vitest/helpers";
import { enableAutoUnmount, shallowMount, type VueWrapper } from "@vue/test-utils";
import { BFormTextarea } from "bootstrap-vue";
import flushPromises from "flush-promises";
import { setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { defineComponent, nextTick } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import type GButton from "@/components/BaseComponents/GButton.vue";
import type GModal from "@/components/BaseComponents/GModal.vue";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { Services } from "@/components/Workflow/services";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { getAppRoot } from "@/onload/loadConfig";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type NewStep, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { getModule, getVersions, saveWorkflow } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";

import Index from "./Index.vue";
import SaveChangesModal from "./SaveChangesModal.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import NodeInspector from "@/components/Workflow/Editor/NodeInspector.vue";
import ReadmeEditor from "@/components/Workflow/Editor/ReadmeEditor.vue";
import WorkflowAttributes from "@/components/Workflow/Editor/WorkflowAttributes.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

const WORKFLOW_ID = "workflow_id";
const GET_APP_ROOT_PREFIX = "prefix/" as const;

const SELECTORS = {
    SAVE_BUTTON: "#workflow-save-button",
    SAVE_AS_MODAL: "[data-description='save-as-modal']",
    ERROR_MODAL: "[data-description='workflow editor error modal']",
};

const localVue = getLocalVue();

const mockFlashSavedIndicator = vi.fn();

/**
 * Stub for `ActivityBar`, a component `Index.vue` calls methods on directly
 * (`activityBar.value?.isActiveSideBar/setActiveSideBar`). Renders its
 * `side-panel` slot, passing `isActiveSideBar` as the `is-active-side-bar`
 * scoped slot prop, so `WorkflowAttributes` etc. render underneath it, and
 * tracks the "active" panel reactively so `showAttributes()` can switch it.
 */
const activityBarStub = defineComponent({
    data(): { activeSideBar: string } {
        return { activeSideBar: "workflow-editor-attributes" };
    },
    methods: {
        isActiveSideBar(this: { activeSideBar: string }, name: string) {
            return this.activeSideBar === name;
        },
        setActiveSideBar(this: { activeSideBar: string }, name: string) {
            this.activeSideBar = name;
        },
    },
    template: `<div><slot name="side-panel" :is-active-side-bar="isActiveSideBar" /></div>`,
});

/** Children whose methods `Index.vue` calls through template refs, which the default auto-stubs lack. */
const EDITOR_STUBS = {
    ActivityBar: activityBarStub,
    // Renders its slot, so the node inspector mounts once a step is active.
    WorkflowGraph: {
        template: "<div><slot /></div>",
        props: ["datatypesMapper"],
        methods: {
            fitWorkflow() {},
            setTransform() {},
        },
    },
    // Called after every successful save.
    ChangesIndicator: {
        template: "<div />",
        methods: {
            flashSavedIndicator: mockFlashSavedIndicator,
        },
    },
};

// vue-router mocks
const mockPush = vi.fn();
const mockReplace = vi.fn();
let mockRoute: { query: Record<string, string>; fullPath: string } = { query: {}, fullPath: "/" };
vi.mock("vue-router", async (importOriginal) => {
    const actual = (await importOriginal()) as Record<string, unknown>;
    return {
        ...actual,
        useRouter: () => ({ push: mockPush, replace: mockReplace }),
        useRoute: () => mockRoute,
    };
});

vi.mock("./modules/services");
vi.mock("@/onload/loadConfig");
vi.mock("./modules/utilities");
vi.mock("@/components/Workflow/workflows.services");

const { server, http } = useServerMock();

const mockGetAppRoot = vi.mocked(getAppRoot);
const mockGetStateUpgradeMessages = vi.mocked(getStateUpgradeMessages);
const mockLoadWorkflow = vi.mocked(getWorkflowFull);
const mockGetVersions = vi.mocked(getVersions);
const mockSaveWorkflow = vi.mocked(saveWorkflow);
const mockGetModule = vi.mocked(getModule);

/**
 * Mounts the editor on a fresh testing Pinia with datatypes already loaded. The
 * returned stores are scoped to the editor's own id, which is a generated uid
 * rather than "workflow_id" when `workflowId` is omitted (a new temp workflow).
 */
function mountEditor(props: Record<string, unknown> = {}) {
    const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
    setActivePinia(pinia);
    useDatatypesMapperStore().datatypesMapper = testDatatypesMapper;

    const wrapper = shallowMount(Index, {
        props: { workflowId: WORKFLOW_ID, initialVersion: 1, workflows: [], toolbox: [], ...props },
        global: { ...withPlugins(localVue, pinia), stubs: { ...localVue.stubs, ...EDITOR_STUBS } },
    });

    const id = wrapper.findComponent(WorkflowAttributes).props("id") as string;
    return { wrapper, stateStore: useWorkflowStateStore(id), stepStore: useWorkflowStepStore(id) };
}

/** Mounts the editor and waits for its initial workflow load to settle. */
async function mountLoadedEditor(props: Record<string, unknown> = {}) {
    const editor = mountEditor(props);
    await flushPromises();
    return editor;
}

function clickActivity(wrapper: VueWrapper, activityId: string) {
    wrapper.findComponent(activityBarStub).vm.$emit("activityClicked", activityId);
}

function toolStep(overrides: Partial<NewStep> & Pick<NewStep, "name">): NewStep {
    return {
        type: "tool",
        content_id: "cat1",
        tool_id: "cat1",
        tool_state: {},
        input_connections: {},
        inputs: [],
        outputs: [],
        position: { left: 0, top: 0 },
        workflow_outputs: [],
        ...overrides,
    };
}

enableAutoUnmount(afterEach);

describe("Index", () => {
    beforeEach(() => {
        vi.resetAllMocks();
        vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 0);
        mockRoute = { query: {}, fullPath: "/" };

        // `useMagicKeys` (undo/redo shortcuts) always wraps a `Set` in `reactive()`
        // TODO: Remove this once we upgrade to Vue 3?
        suppressExpectedErrorMessages(["Vue 2 does not support reactive collection types"]);

        // return the structure expected by `fromSimple`
        mockLoadWorkflow.mockResolvedValue({ steps: {}, comments: [], tags: [] });
        mockGetVersions.mockResolvedValue([]);
        mockGetStateUpgradeMessages.mockImplementation(() => []);
        mockGetAppRoot.mockImplementation(() => GET_APP_ROOT_PREFIX);
        mockUnprivilegedToolsRequest(server, http);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe("default mount", () => {
        function mountDefaultEditor() {
            return mountEditor({ workflowTags: ["moo", "cow"] });
        }

        it("resolves datatypes", async () => {
            const { wrapper } = mountDefaultEditor();
            // The graph renders once the datatypes mapper has resolved.
            await flushPromises();

            const workflowGraph = wrapper.findComponent(WorkflowGraph);

            expect(workflowGraph.props("datatypesMapper")).toEqual(testDatatypesMapper);
            expect(workflowGraph.props("datatypesMapper")).not.toBeNull();
            expect(workflowGraph.props("datatypesMapper")).not.toBeUndefined();
        });

        it("does not have changes once the initial load settles", async () => {
            const { stateStore } = mountDefaultEditor();

            await flushPromises();

            expect(stateStore.hasChanges).toBeFalsy();
        });

        it("assigns a fresh id and uuid when cloning a step, including its workflow_outputs", async () => {
            const { wrapper, stepStore } = mountDefaultEditor();
            await flushPromises();
            const sourceStep = stepStore.addStep(
                toolStep({
                    label: "source label",
                    name: "source step",
                    uuid: "11111111-1111-1111-1111-111111111111",
                    workflow_outputs: [{ output_name: "out1", uuid: "22222222-2222-2222-2222-222222222222" }],
                }),
            );

            wrapper.findComponent(WorkflowGraph).vm.$emit("onClone", String(sourceStep.id));
            await nextTick();

            const clonedStepId = Object.keys(stepStore.steps).find((stepId) => stepId !== String(sourceStep.id))!;
            const clonedStep = stepStore.steps[clonedStepId]!;

            // The clone must not keep the source step's uuid, otherwise saving
            // the workflow fails with "Duplicate step UUID ... in request."
            expect(clonedStep.uuid).not.toBe(sourceStep.uuid);
            expect(clonedStep.label).not.toBe(sourceStep.label);

            // Nor may it keep its workflow_outputs' uuids, otherwise saving fails with
            // "Duplicate workflow output UUID ... in request." instead.
            expect(clonedStep.workflow_outputs?.[0]?.uuid).not.toBe(sourceStep.workflow_outputs?.[0]?.uuid);
        });

        it("routes to download URL and respects Galaxy prefix", async () => {
            const { wrapper } = mountDefaultEditor();
            // A plain object keeps the assigned href as-is, where the location mock would resolve it.
            Object.defineProperty(window, "location", {
                value: { href: "original" },
                writable: true,
            });

            clickActivity(wrapper, "workflow-download");
            await flushPromises();

            expect(window.location.href).toBe(
                `${GET_APP_ROOT_PREFIX}api/workflows/workflow_id/download?format=json-download`,
            );
            expect(window.location.href).not.toBe("api/workflows/workflow_id/download?format=json-download");
        });

        it.each([
            {
                field: "annotation",
                event: "update:annotationCurrent",
                original: "original annotation",
                changed: "new annotation",
            },
            { field: "name", event: "update:nameCurrent", original: "original name", changed: "new name" },
            { field: "help", event: "update:helpCurrent", original: "original help", changed: "new help" },
            {
                field: "logoUrl",
                event: "update:logoUrlCurrent",
                original: "http://example.com/a.png",
                changed: "http://example.com/b.png",
            },
        ])("tracks changes to $field", async ({ event, original, changed }) => {
            const { wrapper, stateStore } = mountDefaultEditor();
            const workflowAttributes = wrapper.findComponent(WorkflowAttributes);
            expect(stateStore.hasChanges).toBeFalsy();

            workflowAttributes.vm.$emit(event, original);
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();

            stateStore.hasChanges = false;
            await nextTick();

            // Re-emitting the same value should not mark the workflow as changed again.
            workflowAttributes.vm.$emit(event, original);
            await nextTick();
            expect(stateStore.hasChanges).toBeFalsy();

            workflowAttributes.vm.$emit(event, changed);
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();
        });

        it("tracks changes to readme", async () => {
            const { wrapper, stateStore } = mountDefaultEditor();
            await flushPromises();
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:readme-active", true);
            await nextTick();
            const readmeEditor = wrapper.findComponent(ReadmeEditor);

            readmeEditor.vm.$emit("update:readmeCurrent", "original readme");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();

            stateStore.hasChanges = false;
            await nextTick();

            // Re-emitting the same value should not mark the workflow as changed again.
            readmeEditor.vm.$emit("update:readmeCurrent", "original readme");
            await nextTick();
            expect(stateStore.hasChanges).toBeFalsy();

            readmeEditor.vm.$emit("update:readmeCurrent", "new readme");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();
        });

        it("closes the readme editor when leaving the attributes activity, but not for undo-redo", async () => {
            const { wrapper } = mountDefaultEditor();
            const activityBar = wrapper.findComponent(activityBarStub);

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:readme-active", true);
            await nextTick();
            expect(wrapper.findComponent(ReadmeEditor).exists()).toBe(true);

            // Switching to the undo-redo activity is the one exception: readme stays open.
            activityBar.vm.setActiveSideBar("workflow-undo-redo");
            await nextTick();
            expect(wrapper.findComponent(ReadmeEditor).exists()).toBe(true);

            // Any other activity closes the readme editor.
            activityBar.vm.setActiveSideBar("workflow-editor-tools");
            await nextTick();
            expect(wrapper.findComponent(ReadmeEditor).exists()).toBe(false);
        });

        it("clears hasChanges after a successful save", async () => {
            mockSaveWorkflow.mockResolvedValue({ version: 1 });
            const { wrapper, stateStore } = mountDefaultEditor();
            await flushPromises();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:annotationCurrent", "a change");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();

            wrapper.findComponent<typeof GButton>(SELECTORS.SAVE_BUTTON).vm.$emit("click");
            await flushPromises();

            expect(mockSaveWorkflow).toHaveBeenCalled();
            expect(stateStore.hasChanges).toBeFalsy();
            expect(mockFlashSavedIndicator).toHaveBeenCalledOnce();
        });

        it("keeps edits made during a save dirty and does not show saved feedback", async () => {
            let resolveSave: (value: { version: number }) => void = () => {};
            mockSaveWorkflow.mockImplementation(
                () =>
                    new Promise<{ version: number }>((resolve) => {
                        resolveSave = resolve;
                    }),
            );
            const { wrapper, stateStore } = mountDefaultEditor();
            await flushPromises();
            const workflowAttributes = wrapper.findComponent(WorkflowAttributes);

            workflowAttributes.vm.$emit("update:annotationCurrent", "submitted annotation");
            await nextTick();
            wrapper.findComponent<typeof GButton>(SELECTORS.SAVE_BUTTON).vm.$emit("click");
            await nextTick();
            workflowAttributes.vm.$emit("update:annotationCurrent", "newer annotation");
            await nextTick();
            resolveSave({ version: 2 });
            await flushPromises();

            expect(mockSaveWorkflow).toHaveBeenCalledWith(
                expect.objectContaining({ annotation: "submitted annotation" }),
            );
            expect(wrapper.findComponent(WorkflowAttributes).props("annotation")).toBe("newer annotation");
            expect(stateStore.hasChanges).toBeTruthy();
            expect(mockFlashSavedIndicator).not.toHaveBeenCalled();
        });

        it("save as calls createWorkflow with the provided name and annotation", async () => {
            const createWorkflowSpy = vi
                .spyOn(Services.prototype, "createWorkflow")
                .mockResolvedValue({ id: "new_id", name: "My New Workflow", number_of_steps: 3 });
            mockSaveWorkflow.mockResolvedValue({ version: 1 });
            const { wrapper } = mountDefaultEditor();

            wrapper.findComponent(GFormInput).vm.$emit("update:modelValue", "My New Workflow");
            // vue-test-utils' auto-stub for `BFormTextarea` declares its own v-model
            // config (`{ prop: "value", event: "update" }`), so the emit event to
            // drive `v-model="saveAsAnnotation"` is "update", not "input".
            wrapper.findComponent(BFormTextarea).vm.$emit("update", "A description");
            await nextTick();

            wrapper.findComponent<typeof GModal>(SELECTORS.SAVE_AS_MODAL).vm.$emit("ok");
            await flushPromises();

            expect(createWorkflowSpy).toHaveBeenCalledWith(
                expect.objectContaining({ name: "My New Workflow", annotation: "A description" }),
            );
            // Rule out the "no name provided" fallback naming, so this is actually
            // checking that the typed-in name was used, not just any call at all.
            expect(createWorkflowSpy).not.toHaveBeenCalledWith(
                expect.objectContaining({ name: expect.stringContaining("SavedAs_") }),
            );
        });

        it("save-as field values are intact when doSaveAs runs (not cleared by close event)", async () => {
            const createWorkflowSpy = vi
                .spyOn(Services.prototype, "createWorkflow")
                .mockResolvedValue({ id: "new_id", name: "My New Workflow", number_of_steps: 1 });
            mockSaveWorkflow.mockResolvedValue({ version: 1 });
            const { wrapper } = mountDefaultEditor();

            wrapper.findComponent(GFormInput).vm.$emit("update:modelValue", "My New Workflow");
            await nextTick();

            wrapper.findComponent<typeof GModal>(SELECTORS.SAVE_AS_MODAL).vm.$emit("ok");
            await flushPromises();

            // if fields were cleared before doSaveAs ran, name would be the "SavedAs_..." fallback
            expect(createWorkflowSpy).toHaveBeenCalledWith(expect.objectContaining({ name: "My New Workflow" }));
        });

        it("resets save-as fields when the modal is cancelled", async () => {
            const { wrapper } = mountDefaultEditor();

            wrapper.findComponent(GFormInput).vm.$emit("update:modelValue", "My New Workflow");
            wrapper.findComponent(BFormTextarea).vm.$emit("update", "A description");
            await nextTick();

            expect(wrapper.findComponent(GFormInput).props("modelValue")).toBe("My New Workflow");

            wrapper.findComponent<typeof GModal>(SELECTORS.SAVE_AS_MODAL).vm.$emit("cancel");
            await nextTick();

            expect(wrapper.findComponent(GFormInput).props("modelValue")).toBeNull();
            expect(wrapper.findComponent({ name: "BFormTextarea" }).props("value")).toBeNull();
        });

        it("prevents navigation only if hasChanges", async () => {
            const { wrapper, stateStore } = mountDefaultEditor();
            expect(stateStore.hasChanges).toBeFalsy();
            expect(wrapper.emitted("update:confirmation")).toBeUndefined();

            const workflowAttributes = wrapper.findComponent(WorkflowAttributes);
            expect(workflowAttributes.exists()).toBe(true);
            workflowAttributes.vm.$emit("update:nameCurrent", "trigger change");
            await nextTick();

            expect(stateStore.hasChanges).toBeTruthy();
            await nextTick();

            const confirmationRequired = emittedArg(wrapper, "update:confirmation");
            expect(confirmationRequired).toBeTruthy();
        });

        describe("Messages modal", () => {
            it("shows an error when clicking Save fails, and clears it once the modal is dismissed", async () => {
                mockSaveWorkflow.mockRejectedValue(new Error("Test error message"));
                const { wrapper } = mountDefaultEditor();
                await flushPromises();

                // save button is disabled initially until a change is made
                expect(wrapper.find(SELECTORS.SAVE_BUTTON).attributes("disabled")).toBeTruthy();

                // simulate WorkflowGraph making a change to enable the Save button
                wrapper.findComponent(WorkflowGraph).vm.$emit("onChange");
                await nextTick();

                // save button is now enabled
                expect(wrapper.find(SELECTORS.SAVE_BUTTON).attributes("disabled")).toBeFalsy();

                wrapper.findComponent<typeof GButton>(SELECTORS.SAVE_BUTTON).vm.$emit("click");
                await flushPromises();

                const modal = wrapper.findComponent<typeof GModal>(SELECTORS.ERROR_MODAL);
                expect(modal.props("show")).toBe(true);
                expect(modal.props("title")).toBe("Saving workflow failed...");
                expect(modal.findComponent(GAlert).props("variant")).toBe("danger");
                // Rule out a stale/leftover title from a previous state, so this is
                // actually checking the error from *this* failed save.
                expect(modal.props("title")).not.toBe("Workflow Editor Error");
                expect(mockFlashSavedIndicator).not.toHaveBeenCalled();

                // dismissing the modal (as a user closing it would) should clear the message
                modal.vm.$emit("close");
                await nextTick();

                expect(wrapper.findComponent<typeof GModal>(SELECTORS.ERROR_MODAL).props("show")).toBe(false);
            });
        });
    });

    describe("module updates from the node inspector", () => {
        function moduleData(toolState: object) {
            return {
                content_id: "cat1",
                inputs: [],
                outputs: [],
                config_form: { inputs: [] },
                tool_state: toolState,
                tool_version: "1.0",
                errors: null,
            };
        }

        /** Mounts a loaded editor with `stepCount` tool steps, the first one active in the node inspector. */
        async function mountWithSteps(stepCount: number) {
            const editor = await mountLoadedEditor();
            const stepIds = Array.from(
                { length: stepCount },
                (_, i) => editor.stepStore.addStep(toolStep({ label: `step ${i}`, name: `step ${i}` })).id,
            );
            editor.stateStore.activeNodeId = stepIds[0]!;
            await nextTick();
            return { ...editor, stepIds };
        }

        function emitDataChanged(wrapper: VueWrapper, stepId: number, data: object) {
            wrapper.findComponent(NodeInspector).vm.$emit("dataChanged", stepId, data);
        }

        afterEach(() => {
            vi.useRealTimers();
        });

        it("skips superseded form edits and applies the latest module response", async () => {
            const { wrapper, stateStore, stepStore, stepIds } = await mountWithSteps(1);
            const stepId = stepIds[0]!;
            vi.useFakeTimers();
            let resolveFirst!: (data: object) => void;
            const firstResponse = new Promise((resolve) => {
                resolveFirst = resolve;
            });
            mockGetModule.mockReturnValueOnce(firstResponse).mockResolvedValueOnce(moduleData({ text: "latest" }));

            emitDataChanged(wrapper, stepId, { text: "first" });
            emitDataChanged(wrapper, stepId, { text: "intermediate" });
            emitDataChanged(wrapper, stepId, { text: "latest" });
            await flushPromises();
            expect(mockGetModule).toHaveBeenCalledTimes(1);

            resolveFirst(moduleData({ text: "first" }));
            await flushPromises();
            expect(stepStore.getStep(stepId)?.tool_state).toEqual({ text: "first" });

            await vi.advanceTimersByTimeAsync(1000);
            await flushPromises();

            expect(mockGetModule).toHaveBeenCalledTimes(2);
            expect(mockGetModule).toHaveBeenLastCalledWith({ text: "latest" }, stepId, stateStore.setLoadingState);
            expect(stepStore.getStep(stepId)?.tool_state).toEqual({ text: "latest" });
        });

        it("applies queued form edits for different steps", async () => {
            const { wrapper, stateStore, stepStore, stepIds } = await mountWithSteps(2);
            const [stepZero, stepOne] = stepIds as [number, number];
            vi.useFakeTimers();
            let resolveFirst!: (data: object) => void;
            const firstResponse = new Promise((resolve) => {
                resolveFirst = resolve;
            });
            const firstEdit = { text: "first" };
            mockGetModule.mockImplementation((requestData) =>
                requestData === firstEdit ? firstResponse : Promise.resolve(moduleData(requestData)),
            );

            emitDataChanged(wrapper, stepOne, firstEdit);
            emitDataChanged(wrapper, stepZero, { text: "step 0" });
            emitDataChanged(wrapper, stepOne, { text: "step 1" });

            resolveFirst(moduleData(firstEdit));
            await flushPromises();
            await vi.advanceTimersByTimeAsync(1000);
            await flushPromises();

            expect(mockGetModule).toHaveBeenCalledWith({ text: "step 0" }, stepZero, stateStore.setLoadingState);
            expect(stepStore.getStep(stepZero)?.tool_state).toEqual({ text: "step 0" });
            expect(stepStore.getStep(stepOne)?.tool_state).toEqual({ text: "step 1" });
        });
    });

    // The "exit" activity navigates to "/workflows/list" through `onNavigate`, with no forceSave/appendVersion.
    describe("onNavigate", () => {
        /** Marks the workflow as changed via a real user-facing event (annotation
         * update through `WorkflowAttributes`), rather than reaching into internals. */
        async function makeChange({ wrapper, stateStore }: ReturnType<typeof mountEditor>) {
            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:annotationCurrent", "trigger change");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();
        }

        /** Picks "Save" (forceSave) or "Don't Save" (ignoreChanges) in the save-changes modal. */
        function proceedFromSaveChangesModal(wrapper: VueWrapper, choice: "save" | "dontSave") {
            const [forceSave, ignoreChanges] = choice === "save" ? [true, false] : [false, true];
            wrapper
                .findComponent(SaveChangesModal)
                .vm.$emit("on-proceed", "/workflows/list", forceSave, ignoreChanges, false);
        }

        beforeEach(() => {
            mockSaveWorkflow.mockResolvedValue({ version: 1 });
        });

        it("navigates immediately when there are no unsaved changes", async () => {
            const { wrapper } = await mountLoadedEditor();

            clickActivity(wrapper, "exit");
            await flushPromises();

            expect(wrapper.findComponent(SaveChangesModal).props("showModal")).toBe(false);
            expect(mockSaveWorkflow).not.toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith("/workflows/list");
        });

        it("shows the save-changes modal instead of navigating when there are unsaved changes", async () => {
            const editor = await mountLoadedEditor();
            await makeChange(editor);

            clickActivity(editor.wrapper, "exit");
            await flushPromises();

            expect(mockPush).not.toHaveBeenCalled();
            const modal = editor.wrapper.findComponent(SaveChangesModal);
            expect(modal.props("showModal")).toBe(true);
            expect(modal.props("navUrl")).toBe("/workflows/list");
        });

        it("does not navigate and keeps changes when the save-changes modal is cancelled", async () => {
            const editor = await mountLoadedEditor();
            const { wrapper, stateStore } = editor;
            await makeChange(editor);
            clickActivity(wrapper, "exit");
            await nextTick();

            wrapper.findComponent(SaveChangesModal).vm.$emit("update:show-modal", false);
            await nextTick();

            expect(mockPush).not.toHaveBeenCalled();
            expect(mockSaveWorkflow).not.toHaveBeenCalled();
            expect(stateStore.hasChanges).toBeTruthy();
            expect(wrapper.findComponent(SaveChangesModal).props("showModal")).toBe(false);
        });

        it("navigates without saving when the save-changes modal's Don't Save is chosen", async () => {
            const editor = await mountLoadedEditor();
            const { wrapper, stateStore } = editor;
            await makeChange(editor);
            clickActivity(wrapper, "exit");
            await nextTick();

            proceedFromSaveChangesModal(wrapper, "dontSave");
            await flushPromises();

            expect(mockSaveWorkflow).not.toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith("/workflows/list");
            expect(stateStore.hasChanges).toBeFalsy();
        });

        it("saves before navigating when the save-changes modal's Save is chosen", async () => {
            const editor = await mountLoadedEditor();
            const { wrapper, stateStore } = editor;
            mockSaveWorkflow.mockResolvedValue({ version: 2 });
            await makeChange(editor);
            clickActivity(wrapper, "exit");
            await nextTick();

            proceedFromSaveChangesModal(wrapper, "save");
            await flushPromises();

            expect(mockSaveWorkflow).toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith("/workflows/list");
            expect(stateStore.hasChanges).toBeFalsy();
        });

        it("does not navigate if forced save fails", async () => {
            const editor = await mountLoadedEditor();
            const { wrapper } = editor;
            mockSaveWorkflow.mockRejectedValue(new Error("boom"));
            await makeChange(editor);
            clickActivity(wrapper, "exit");
            await nextTick();

            proceedFromSaveChangesModal(wrapper, "save");
            await flushPromises();

            expect(mockSaveWorkflow).toHaveBeenCalled();
            expect(mockPush).not.toHaveBeenCalled();

            // The modal latches `busy` on Save and only clears it when it is shown again,
            // so leaving it open here would disable Cancel/Don't Save/Save with no way
            // back but the close icon. It must close so the error modal is visible.
            expect(wrapper.findComponent(SaveChangesModal).props("showModal")).toBe(false);
        });

        it("appends the current version to the URL when appendVersion is true", async () => {
            const { wrapper } = await mountLoadedEditor();

            // "workflow-run" activity routes via `onRun()`, which calls
            // `onNavigate(..., false, false, true)` — appendVersion=true.
            clickActivity(wrapper, "workflow-run");
            await flushPromises();

            expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("&version="));
        });

        it("creates (rather than just saving) a new temp workflow when forced to save on navigate", async () => {
            // no workflowId prop => isNewTempWorkflow is true
            const editor = await mountLoadedEditor({ workflowId: undefined });
            const createWorkflowSpy = vi
                .spyOn(Services.prototype, "createWorkflow")
                .mockResolvedValue({ id: "new_id", name: "Unnamed Workflow", number_of_steps: 0 });

            await makeChange(editor);
            clickActivity(editor.wrapper, "exit");
            await nextTick();

            proceedFromSaveChangesModal(editor.wrapper, "save");
            await flushPromises();

            // onCreate() is used (not a plain onSave()) to persist the brand-new workflow;
            // onCreate() itself calls routeToWorkflow(), which does its own follow-up save
            // once the workflow has a real id, so saveWorkflow is expected to run after create.
            expect(createWorkflowSpy).toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith("/workflows/list");
            expect(mockFlashSavedIndicator).toHaveBeenCalledOnce();
        });

        it("emits forceReload instead of pushing when navigating to the exact current route", async () => {
            mockRoute = { query: {}, fullPath: "/workflows/list" };
            const { wrapper } = await mountLoadedEditor();

            clickActivity(wrapper, "exit");
            await flushPromises();

            expect(mockPush).not.toHaveBeenCalled();
            expect(wrapper.emitted("forceReload")).toBeTruthy();
        });

        it("does not emit forceReload when navigating to a different route", async () => {
            mockRoute = { query: {}, fullPath: "/workflows/edit" };
            const { wrapper } = await mountLoadedEditor();

            clickActivity(wrapper, "exit");
            await flushPromises();

            expect(wrapper.emitted("forceReload")).toBeFalsy();
        });

        it("createNewWorkflow routes through onNavigate and its unsaved-changes guard", async () => {
            const { wrapper } = await mountLoadedEditor();

            // "workflow-create" activity routes via `createNewWorkflow()`, which
            // calls `onNavigate("/workflows/edit")` with no unsaved changes.
            clickActivity(wrapper, "workflow-create");
            await flushPromises();

            expect(mockPush).toHaveBeenCalledWith("/workflows/edit");
        });
    });
});
