import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, mockUnprivilegedToolsRequest, suppressExpectedErrorMessages } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import { BFormTextarea } from "bootstrap-vue";
import flushPromises from "flush-promises";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import Vue, { nextTick } from "vue";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { Services } from "@/components/Workflow/services";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { getAppRoot } from "@/onload/loadConfig";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";

import { getVersions, saveWorkflow } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";

import Index from "./Index.vue";
import SaveChangesModal from "./SaveChangesModal.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import ReadmeEditor from "@/components/Workflow/Editor/ReadmeEditor.vue";
import WorkflowAttributes from "@/components/Workflow/Editor/WorkflowAttributes.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

const GET_APP_ROOT_PREFIX = "prefix/" as const;
// Selectors
const SELECTORS = {
    WORKFLOW_GRAPH: '[data-description="workflow graph in editor"]',
    ACTIVITY_BAR: '[data-description="workflow editor activity bar"]',
} as const;

// `<script setup>` SFCs compile to nameless component objects (their inferred
// name lives on `__name`, which vue-test-utils 1.x doesn't read). Since
// `Index.vue` is itself `<script setup>`, it resolves these children as direct
// object references rather than string tags, so vue-test-utils' `stubs` option
// (which matches by `.name`) can never target them unless we set `.name`
// ourselves on the shared imported component object before mounting.
(ActivityBar as unknown as { name?: string }).name = "ActivityBar";
(WorkflowGraph as unknown as { name?: string }).name = "WorkflowGraph";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);

/**
 * Stub for `ActivityBar`, a component `Index.vue` calls methods on directly
 * (`activityBar.value?.isActiveSideBar/setActiveSideBar`). Renders its
 * `side-panel` slot so `WorkflowAttributes` etc. render underneath it, and
 * tracks the "active" panel reactively so `showAttributes()` can switch it.
 */
const activityBarStub = Vue.extend({
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
    template: `<div><slot name="side-panel" /></div>`,
});

function editorStubs() {
    return {
        ActivityBar: activityBarStub,
        WorkflowGraph: {
            template: "<div />",
            props: ["datatypesMapper"],
            methods: {
                fitWorkflow() {},
                setTransform() {},
            },
        },
    };
}

// vue-router mocks
const mockPush = vi.fn();
const mockReplace = vi.fn();
let mockRoute: { query: Record<string, string>; fullPath: string } = { query: {}, fullPath: "/" };
vi.mock("vue-router/composables", () => ({
    useRouter: () => ({ push: mockPush, replace: mockReplace }),
    useRoute: () => mockRoute,
}));

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

describe("Index", () => {
    beforeEach(() => {
        vi.spyOn(window, "requestAnimationFrame").mockImplementation(() => 0);

        mockPush.mockClear();
        mockReplace.mockClear();
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

    describe("default mount", () => {
        let wrapper: Wrapper<Vue>;
        let stateStore: ReturnType<typeof useWorkflowStateStore>;

        beforeEach(() => {
            const testingPinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
            setActivePinia(testingPinia);
            const datatypesStore = useDatatypesMapperStore();
            datatypesStore.datatypesMapper = testDatatypesMapper;

            stateStore = useWorkflowStateStore("workflow_id");

            wrapper = shallowMount(Index as object, {
                propsData: {
                    workflowId: "workflow_id",
                    initialVersion: 1,
                    workflowTags: ["moo", "cow"],
                    workflows: [],
                    toolbox: [],
                },
                localVue,
                pinia: testingPinia,
                // mock out components that have exposed methods used by Index.vue.
                stubs: editorStubs(),
            });
        });

        async function resetChanges() {
            stateStore.hasChanges = false;
            await nextTick();
        }

        it("resolves datatypes", async () => {
            const workflowGraph = wrapper.find(SELECTORS.WORKFLOW_GRAPH);

            expect(workflowGraph.props("datatypesMapper")).toEqual(testDatatypesMapper);
            expect(workflowGraph.props("datatypesMapper")).not.toBeNull();
            expect(workflowGraph.props("datatypesMapper")).not.toBeUndefined();
        });

        it("does not have changes once the initial load settles", async () => {
            await flushPromises();
            expect(stateStore.hasChanges).toBeFalsy();
        });

        it("assigns a fresh id and uuid when cloning a step", async () => {
            await flushPromises();

            const stepStore = useWorkflowStepStore("workflow_id");
            const sourceStep = stepStore.addStep({
                type: "tool",
                label: "source label",
                name: "source step",
                content_id: "cat1",
                tool_id: "cat1",
                tool_state: {},
                input_connections: {},
                inputs: [],
                outputs: [],
                position: { left: 0, top: 0 },
                uuid: "11111111-1111-1111-1111-111111111111",
            });

            wrapper.find(SELECTORS.WORKFLOW_GRAPH).vm.$emit("onClone", String(sourceStep.id));
            await nextTick();

            const clonedStepId = Object.keys(stepStore.steps).find((stepId) => stepId !== String(sourceStep.id))!;
            const clonedStep = stepStore.steps[clonedStepId]!;

            // The clone must not keep the source step's uuid, otherwise saving
            // the workflow fails with "Duplicate step UUID ... in request."
            expect(clonedStep.uuid).not.toBe(sourceStep.uuid);
            expect(clonedStep.label).not.toBe(sourceStep.label);
        });

        it("routes to download URL and respects Galaxy prefix", async () => {
            Object.defineProperty(window, "location", {
                value: { href: "original" },
                writable: true,
            });

            wrapper.find(SELECTORS.ACTIVITY_BAR).vm.$emit("activityClicked", "workflow-download");
            await flushPromises();

            expect(window.location.href).toBe(
                `${GET_APP_ROOT_PREFIX}api/workflows/workflow_id/download?format=json-download`,
            );
            expect(window.location.href).not.toBe("api/workflows/workflow_id/download?format=json-download");
        });

        it("tracks changes to annotations", async () => {
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:annotationCurrent", "original annotation");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();

            await resetChanges();

            // Re-emitting the same value should not mark the workflow as changed again.
            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:annotationCurrent", "original annotation");
            await nextTick();
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:annotationCurrent", "new annotation");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();
        });

        it("tracks changes to name", async () => {
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:nameCurrent", "original name");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();

            await resetChanges();

            // Re-emitting the same value should not mark the workflow as changed again.
            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:nameCurrent", "original name");
            await nextTick();
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:nameCurrent", "new name");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();
        });

        it("tracks changes to help", async () => {
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:helpCurrent", "original help");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();

            await resetChanges();

            // Re-emitting the same value should not mark the workflow as changed again.
            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:helpCurrent", "original help");
            await nextTick();
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:helpCurrent", "new help");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();
        });

        it("tracks changes to logoUrl", async () => {
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:logoUrlCurrent", "http://example.com/a.png");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();

            await resetChanges();

            // Re-emitting the same value should not mark the workflow as changed again.
            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:logoUrlCurrent", "http://example.com/a.png");
            await nextTick();
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:logoUrlCurrent", "http://example.com/b.png");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();
        });

        it("tracks changes to readme", async () => {
            // wait for the initial workflow load to settle before making changes.
            await flushPromises();
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:readme-active", true);
            await nextTick();

            wrapper.findComponent(ReadmeEditor).vm.$emit("update:readmeCurrent", "original readme");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();

            await resetChanges();

            // Re-emitting the same value should not mark the workflow as changed again.
            wrapper.findComponent(ReadmeEditor).vm.$emit("update:readmeCurrent", "original readme");
            await nextTick();
            expect(stateStore.hasChanges).toBeFalsy();

            wrapper.findComponent(ReadmeEditor).vm.$emit("update:readmeCurrent", "new readme");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();
        });

        it("closes the readme editor when leaving the attributes activity, but not for undo-redo", async () => {
            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:readme-active", true);
            await nextTick();
            expect(wrapper.findComponent(ReadmeEditor).exists()).toBe(true);

            // Switching to the undo-redo activity is the one exception: readme stays open.
            (wrapper.find(SELECTORS.ACTIVITY_BAR).vm as InstanceType<typeof activityBarStub>).setActiveSideBar(
                "workflow-undo-redo",
            );
            await nextTick();
            expect(wrapper.findComponent(ReadmeEditor).exists()).toBe(true);

            // Any other activity closes the readme editor.
            (wrapper.find(SELECTORS.ACTIVITY_BAR).vm as InstanceType<typeof activityBarStub>).setActiveSideBar(
                "workflow-editor-tools",
            );
            await nextTick();
            expect(wrapper.findComponent(ReadmeEditor).exists()).toBe(false);
        });

        it("clears hasChanges after a successful save", async () => {
            mockSaveWorkflow.mockResolvedValue({ version: 1 });

            // wait for the initial workflow load to settle before making changes.
            await flushPromises();

            wrapper.findComponent(WorkflowAttributes).vm.$emit("update:annotationCurrent", "a change");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();

            wrapper.find("#workflow-save-button").vm!.$emit("click");
            await flushPromises();

            expect(mockSaveWorkflow).toHaveBeenCalled();
            expect(stateStore.hasChanges).toBeFalsy();
        });

        it("save as calls createWorkflow with the provided name and annotation", async () => {
            const createWorkflowSpy = vi
                .spyOn(Services.prototype, "createWorkflow")
                .mockResolvedValue({ id: "new_id", name: "My New Workflow", number_of_steps: 3 });
            mockSaveWorkflow.mockResolvedValue({ version: 1 });

            wrapper.findComponent(GFormInput).vm.$emit("input", "My New Workflow");
            // vue-test-utils' auto-stub for `BFormTextarea` declares its own v-model
            // config (`{ prop: "value", event: "update" }`), so the emit event to
            // drive `v-model="saveAsAnnotation"` is "update", not "input".
            wrapper.findComponent(BFormTextarea).vm.$emit("update", "A description");
            await nextTick();

            wrapper.find("[data-description='save-as-modal']").vm.$emit("ok");
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

            wrapper.findComponent(GFormInput).vm.$emit("input", "My New Workflow");
            await nextTick();

            wrapper.find("[data-description='save-as-modal']").vm.$emit("ok");
            await flushPromises();

            // if fields were cleared before doSaveAs ran, name would be the "SavedAs_..." fallback
            expect(createWorkflowSpy).toHaveBeenCalledWith(expect.objectContaining({ name: "My New Workflow" }));
        });

        it("resets save-as fields when the modal is cancelled", async () => {
            wrapper.findComponent(GFormInput).vm.$emit("input", "My New Workflow");
            wrapper.findComponent(BFormTextarea).vm.$emit("update", "A description");
            await nextTick();

            expect(wrapper.findComponent(GFormInput).props("value")).toBe("My New Workflow");

            wrapper.find("[data-description='save-as-modal']").vm.$emit("cancel");
            await nextTick();

            expect(wrapper.findComponent(GFormInput).props("value")).toBeNull();
            expect(wrapper.findComponent(BFormTextarea).props("value")).toBeNull();
        });

        it("prevents navigation only if hasChanges", async () => {
            expect(stateStore.hasChanges).toBeFalsy();

            const workflowAttributes = wrapper.findComponent(WorkflowAttributes);
            expect(workflowAttributes.exists()).toBe(true);
            workflowAttributes.vm.$emit("update:nameCurrent", "trigger change");
            await nextTick();

            expect(stateStore.hasChanges).toBeTruthy();
            await nextTick();

            const confirmationRequired = wrapper.emitted()["update:confirmation"]![0]![0];
            expect(confirmationRequired).toBeTruthy();
        });

        describe("Messages modal", () => {
            it("shows an error when clicking Save fails, and clears it once the modal is dismissed", async () => {
                mockSaveWorkflow.mockRejectedValue(new Error("Test error message"));

                // wait for workflow to load
                await flushPromises();

                // save button is disabled initially until a change is made
                expect(wrapper.find("#workflow-save-button").attributes("disabled")).toBeTruthy();

                // simulate WorkflowGraph making a change to enable the Save button
                wrapper.find(SELECTORS.WORKFLOW_GRAPH).vm.$emit("onChange");
                await nextTick();

                // save button is now enabled
                expect(wrapper.find("#workflow-save-button").attributes("disabled")).toBeFalsy();

                wrapper.find("#workflow-save-button").vm!.$emit("click");
                await flushPromises();

                const modal = wrapper.find("[data-description='workflow editor error modal']");
                expect(modal.props("show")).toBe(true);
                expect(modal.props("title")).toBe("Saving workflow failed...");
                expect(modal.findComponent(GAlert).props("variant")).toBe("danger");
                // Rule out a stale/leftover title from a previous state, so this is
                // actually checking the error from *this* failed save.
                expect(modal.props("title")).not.toBe("Workflow Editor Error");

                // dismissing the modal (as a user closing it would) should clear the message
                modal.vm.$emit("close");
                await nextTick();

                expect(wrapper.find("[data-description='workflow editor error modal']").props("show")).toBe(false);
            });
        });
    });

    describe("onNavigate", () => {
        let stateStore: ReturnType<typeof useWorkflowStateStore>;

        /** Mounts a fresh Index instance, so route state (and router.push call
         * history) never leaks between these tests. */
        async function mountForNav(propsData: Record<string, unknown> = {}) {
            const testingPinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
            setActivePinia(testingPinia);
            const datatypesStore = useDatatypesMapperStore();
            datatypesStore.datatypesMapper = testDatatypesMapper;

            const w = shallowMount(Index as object, {
                propsData: {
                    workflowId: "workflow_id",
                    initialVersion: 1,
                    workflowTags: [],
                    workflows: [],
                    toolbox: [],
                    ...propsData,
                },
                localVue,
                pinia: testingPinia,
                stubs: editorStubs(),
            });
            await flushPromises();

            // When `workflowId` is omitted (new temp workflow), `Index.vue` scopes
            // its stores to a randomly generated uid, not "workflow_id" — read the
            // actual id `WorkflowAttributes` was given rather than guessing it.
            const resolvedId = w.findComponent(WorkflowAttributes).props("id") as string;
            stateStore = useWorkflowStateStore(resolvedId);

            return w;
        }

        /** Marks the workflow as changed via a real user-facing event (annotation
         * update through `WorkflowAttributes`), rather than reaching into internals. */
        async function triggerHasChanges(w: Wrapper<Vue>) {
            w.findComponent(WorkflowAttributes).vm.$emit("update:annotationCurrent", "trigger change");
            await nextTick();
            expect(stateStore.hasChanges).toBeTruthy();
        }

        /** `Index.vue` never exposes `onNavigate` directly; the "exit" activity
         * routes to "/workflows/list" through it with no forceSave/appendVersion,
         * matching what these tests exercise. */
        async function triggerOnNavigateToList(w: Wrapper<Vue>) {
            w.find(SELECTORS.ACTIVITY_BAR).vm.$emit("activityClicked", "exit");
        }

        beforeEach(() => {
            mockSaveWorkflow.mockReset();
            mockSaveWorkflow.mockResolvedValue({ version: 1 });
        });

        it("navigates immediately when there are no unsaved changes", async () => {
            const wrapper = await mountForNav();

            await triggerOnNavigateToList(wrapper);
            await flushPromises();

            expect(wrapper.findComponent(SaveChangesModal).props("showModal")).toBe(false);
            expect(mockSaveWorkflow).not.toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith("/workflows/list");
        });

        it("shows the save-changes modal instead of navigating when there are unsaved changes", async () => {
            const wrapper = await mountForNav();
            await triggerHasChanges(wrapper);

            await triggerOnNavigateToList(wrapper);
            await flushPromises();

            expect(mockPush).not.toHaveBeenCalled();
            const modal = wrapper.findComponent(SaveChangesModal);
            expect(modal.props("showModal")).toBe(true);
            expect(modal.props("navUrl")).toBe("/workflows/list");
        });

        it("does not navigate and keeps changes when the save-changes modal is cancelled", async () => {
            const wrapper = await mountForNav();
            await triggerHasChanges(wrapper);
            await triggerOnNavigateToList(wrapper);
            await nextTick();

            wrapper.findComponent(SaveChangesModal).vm.$emit("update:show-modal", false);
            await nextTick();

            expect(mockPush).not.toHaveBeenCalled();
            expect(mockSaveWorkflow).not.toHaveBeenCalled();
            expect(stateStore.hasChanges).toBeTruthy();
            expect(wrapper.findComponent(SaveChangesModal).props("showModal")).toBe(false);
        });

        it("navigates without saving when the save-changes modal's Don't Save is chosen", async () => {
            const wrapper = await mountForNav();
            await triggerHasChanges(wrapper);
            await triggerOnNavigateToList(wrapper);
            await nextTick();

            // "Don't Save": on-proceed emitted with forceSave=false, ignoreChanges=true
            wrapper.findComponent(SaveChangesModal).vm.$emit("on-proceed", "/workflows/list", false, true, false);
            await flushPromises();

            expect(mockSaveWorkflow).not.toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith("/workflows/list");
            expect(stateStore.hasChanges).toBeFalsy();
        });

        it("saves before navigating when the save-changes modal's Save is chosen", async () => {
            const wrapper = await mountForNav();
            mockSaveWorkflow.mockResolvedValue({ version: 2 });
            await triggerHasChanges(wrapper);
            await triggerOnNavigateToList(wrapper);
            await nextTick();

            // "Save": on-proceed emitted with forceSave=true, ignoreChanges=false
            wrapper.findComponent(SaveChangesModal).vm.$emit("on-proceed", "/workflows/list", true, false, false);
            await flushPromises();

            expect(mockSaveWorkflow).toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith("/workflows/list");
            expect(stateStore.hasChanges).toBeFalsy();
        });

        it("does not navigate if forced save fails", async () => {
            const wrapper = await mountForNav();
            mockSaveWorkflow.mockRejectedValue(new Error("boom"));
            await triggerHasChanges(wrapper);
            await triggerOnNavigateToList(wrapper);
            await nextTick();

            // "Save": on-proceed emitted with forceSave=true, ignoreChanges=false
            wrapper.findComponent(SaveChangesModal).vm.$emit("on-proceed", "/workflows/list", true, false, false);
            await flushPromises();

            expect(mockSaveWorkflow).toHaveBeenCalled();
            expect(mockPush).not.toHaveBeenCalled();
        });

        it("appends the current version to the URL when appendVersion is true", async () => {
            const wrapper = await mountForNav();

            // "workflow-run" activity routes via `onRun()`, which calls
            // `onNavigate(..., false, false, true)` — appendVersion=true.
            wrapper.find(SELECTORS.ACTIVITY_BAR).vm.$emit("activityClicked", "workflow-run");
            await flushPromises();

            expect(mockPush).toHaveBeenCalledWith(expect.stringContaining("&version="));
        });

        it("creates (rather than just saving) a new temp workflow when forced to save on navigate", async () => {
            // no workflowId prop => isNewTempWorkflow is true
            const wrapper = await mountForNav({ workflowId: undefined });
            const createWorkflowSpy = vi
                .spyOn(Services.prototype, "createWorkflow")
                .mockResolvedValue({ id: "new_id", name: "Unnamed Workflow", number_of_steps: 0 });
            mockSaveWorkflow.mockClear();

            await triggerHasChanges(wrapper);
            await triggerOnNavigateToList(wrapper);
            await nextTick();

            // "Save": on-proceed emitted with forceSave=true, ignoreChanges=false
            wrapper.findComponent(SaveChangesModal).vm.$emit("on-proceed", "/workflows/list", true, false, false);
            await flushPromises();

            // onCreate() is used (not a plain onSave()) to persist the brand-new workflow;
            // onCreate() itself calls routeToWorkflow(), which does its own follow-up save
            // once the workflow has a real id, so saveWorkflow is expected to run after create.
            expect(createWorkflowSpy).toHaveBeenCalled();
            expect(mockPush).toHaveBeenCalledWith("/workflows/list");
        });

        it("emits forceReload instead of pushing when navigating to the exact current route", async () => {
            mockRoute = { query: {}, fullPath: "/workflows/list" };
            const wrapper = await mountForNav();

            await triggerOnNavigateToList(wrapper);
            await flushPromises();

            expect(mockPush).not.toHaveBeenCalled();
            expect(wrapper.emitted().forceReload).toBeTruthy();
        });

        it("does not emit forceReload when navigating to a different route", async () => {
            mockRoute = { query: {}, fullPath: "/workflows/edit" };
            const wrapper = await mountForNav();

            await triggerOnNavigateToList(wrapper);
            await flushPromises();

            expect(wrapper.emitted().forceReload).toBeFalsy();
        });

        it("createNewWorkflow routes through onNavigate and its unsaved-changes guard", async () => {
            const wrapper = await mountForNav();

            // "workflow-create" activity routes via `createNewWorkflow()`, which
            // calls `onNavigate("/workflows/edit")` with no unsaved changes.
            wrapper.find(SELECTORS.ACTIVITY_BAR).vm.$emit("activityClicked", "workflow-create");
            await flushPromises();

            expect(mockPush).toHaveBeenCalledWith("/workflows/edit");
        });
    });
});
