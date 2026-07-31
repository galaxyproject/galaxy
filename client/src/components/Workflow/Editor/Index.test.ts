import { createTestingPinia } from "@pinia/testing";
import { getLocalVue, injectTestRouter, mockUnprivilegedToolsRequest } from "@tests/vitest/helpers";
import { shallowMount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { PiniaVuePlugin, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { testDatatypesMapper } from "@/components/Datatypes/test_fixtures";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { getAppRoot } from "@/onload/loadConfig";
import { useDatatypesMapperStore } from "@/stores/datatypesMapperStore";
import type { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";

import { getVersions, saveWorkflow } from "./modules/services";
import { getStateUpgradeMessages } from "./modules/utilities";

import Index from "./Index.vue";
import SaveChangesModal from "./SaveChangesModal.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";

const localVue = getLocalVue();
localVue.use(PiniaVuePlugin);
const router = injectTestRouter(localVue);

vi.mock("components/Datatypes/factory", () => ({}));
vi.mock("./modules/services");
vi.mock("@/onload/loadConfig");
vi.mock("./modules/utilities");
vi.mock("@/components/Workflow/workflows.services");

vi.mock("app", () => ({}));

const { server, http } = useServerMock();

const mockGetAppRoot = vi.mocked(getAppRoot);
const mockGetStateUpgradeMessages = vi.mocked(getStateUpgradeMessages);
const mockLoadWorkflow = vi.mocked(getWorkflowFull);
const MockGetVersions = vi.mocked(getVersions);
const mockSaveWorkflow = vi.mocked(saveWorkflow);

/** TODO: A potentially hacky type until we modernize the entire
 * component to Composition API and TypeScript */
type IndexComponent = Vue & {
    annotation: string | null;
    name: string | null;
    stateStore: ReturnType<typeof useWorkflowStateStore>;
    datatypesMapper: ReturnType<typeof useDatatypesMapperStore> | null;
    datatypes: Record<string, string[]> | null;
    onDownload: () => void;
    onChange: () => void;
    saveAsName: string | null;
    saveAsAnnotation: string | null;
    services: { createWorkflow: ReturnType<typeof vi.fn> } | null;
    routeToWorkflow: () => Promise<void>;
    hasChanges: boolean;
    isNewTempWorkflow: boolean;
    onNavigate: (url: string, forceSave?: boolean, ignoreChanges?: boolean, appendVersion?: boolean) => Promise<void>;
    createNewWorkflow: () => Promise<void>;
};

describe("Index", () => {
    let wrapper: Wrapper<IndexComponent>;

    beforeEach(() => {
        const testingPinia = createTestingPinia({ createSpy: vi.fn });
        setActivePinia(testingPinia);
        const datatypesStore = useDatatypesMapperStore();
        datatypesStore.datatypesMapper = testDatatypesMapper;
        mockLoadWorkflow.mockResolvedValue({ steps: {} });
        MockGetVersions.mockResolvedValue([]);
        mockGetStateUpgradeMessages.mockImplementation(() => []);
        mockGetAppRoot.mockImplementation(() => "prefix/");
        Object.defineProperty(window, "onbeforeunload", {
            value: null,
            writable: true,
        });
        mockUnprivilegedToolsRequest(server, http);
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
            router,
            // mock out components that have exposed methods used by Index.vue.
            stubs: {
                ActivityBar: {
                    template: "<div />",
                    methods: {
                        isActiveSideBar(name: string) {
                            return name === "workflow-editor-tools";
                        },
                    },
                    expose: ["isActiveSideBar"],
                },
                WorkflowGraph: {
                    template: "<div />",
                    methods: {
                        fitWorkflow() {},
                    },
                    expose: ["fitWorkflow"],
                },
            },
        });
    });

    // Methods to handle the `hasChanges` ref. Once we modernize, we can just use the store directly.
    function getHasChanges() {
        return wrapper.vm.stateStore.hasChanges;
    }
    async function resetChanges() {
        setHasChanges(false);
        await wrapper.vm.$nextTick();
    }
    function setHasChanges(value: boolean) {
        wrapper.vm.stateStore.hasChanges = value;
    }

    it("resolves datatypes", async () => {
        expect(wrapper.vm.datatypesMapper).not.toBeNull();
        expect(wrapper.vm.datatypes).not.toBeNull();
    });

    it("routes to download URL and respects Galaxy prefix", async () => {
        Object.defineProperty(window, "location", {
            value: "original",
            writable: true,
        });
        wrapper.vm.onDownload();
        expect(window.location).toBe("prefix/api/workflows/workflow_id/download?format=json-download");
    });

    it("tracks changes to annotations", async () => {
        expect(getHasChanges()).toBeFalsy();
        wrapper.vm.annotation = "original annotation";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeTruthy();

        await resetChanges();

        wrapper.vm.annotation = "original annotation";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeFalsy();

        wrapper.vm.annotation = "new annotation";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeTruthy();
    });

    it("tracks changes to name", async () => {
        expect(getHasChanges()).toBeFalsy();
        wrapper.vm.name = "original name";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeTruthy();

        await resetChanges();

        wrapper.vm.name = "original name";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeFalsy();

        wrapper.vm.name = "new name";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeTruthy();
    });

    it("save as calls createWorkflow with the provided name and annotation", async () => {
        const vm = wrapper.vm;
        vm.saveAsName = "My New Workflow";
        vm.saveAsAnnotation = "A description";
        vm.services = {
            createWorkflow: vi.fn().mockResolvedValue({ id: "new_id", name: "My New Workflow", number_of_steps: 3 }),
        };
        vi.spyOn(vm, "routeToWorkflow").mockResolvedValue(undefined);

        wrapper.find("[data-description='save-as-modal']").vm.$emit("ok");
        await flushPromises();

        expect(vm.services.createWorkflow).toHaveBeenCalledWith(
            expect.objectContaining({ name: "My New Workflow", annotation: "A description" }),
        );
    });

    it("save-as field values are intact when doSaveAs runs (not cleared by close event)", async () => {
        const vm = wrapper.vm;
        vm.saveAsName = "My New Workflow";
        vm.services = {
            createWorkflow: vi.fn().mockResolvedValue({ id: "new_id", name: "My New Workflow", number_of_steps: 1 }),
        };
        vi.spyOn(vm, "routeToWorkflow").mockResolvedValue(undefined);

        wrapper.find("[data-description='save-as-modal']").vm.$emit("ok");
        await flushPromises();

        // if fields were cleared before doSaveAs ran, name would be the "SavedAs_..." fallback
        expect(vm.services.createWorkflow).toHaveBeenCalledWith(expect.objectContaining({ name: "My New Workflow" }));
    });

    it("resets save-as fields when the modal is cancelled", async () => {
        const vm = wrapper.vm;
        vm.saveAsName = "My New Workflow";
        vm.saveAsAnnotation = "A description";

        wrapper.find("[data-description='save-as-modal']").vm.$emit("cancel");
        await wrapper.vm.$nextTick();

        expect(vm.saveAsName).toBeNull();
        expect(vm.saveAsAnnotation).toBeNull();
    });

    it("prevents navigation only if hasChanges", async () => {
        expect(getHasChanges()).toBeFalsy();
        // Trigger hasChanges via the name watcher rather than calling onChange() directly,
        // because direct method invocation doesn't propagate through createTestingPinia's
        // store mutation tracking with Vite 8's module processing.
        wrapper.vm.name = "trigger change";
        await wrapper.vm.$nextTick();
        expect(getHasChanges()).toBeTruthy();
        await wrapper.vm.$nextTick();
        const confirmationRequired = wrapper.emitted()["update:confirmation"]![0]![0];
        expect(confirmationRequired).toBeTruthy();
    });

    describe("Messages modal", () => {
        it("shows an error when clicking Save fails, and clears it once the modal is dismissed", async () => {
            mockSaveWorkflow.mockRejectedValue(new Error("Test error message"));

            // wait for workflow to load
            await flushPromises();

            // save button is disabled initially until a change is made
            const saveButton = wrapper.find("#workflow-save-button");
            expect(saveButton.attributes("disabled")).toBeTruthy();

            // simulate WorkflowGraph making a change to enable the Save button
            wrapper.findComponent({ ref: "workflowGraph" }).vm.$emit("onChange");
            await wrapper.vm.$nextTick();

            // save button is now enabled
            expect(saveButton.attributes("disabled")).toBeFalsy();

            await saveButton.trigger("click");
            await flushPromises();

            const modal = wrapper.find("[data-description='workflow editor error modal']");
            expect(modal.props("show")).toBe(true);
            expect(modal.props("title")).toBe("Saving workflow failed...");
            expect(modal.findComponent(GAlert).props("variant")).toBe("danger");

            // dismissing the modal (as a user closing it would) should clear the message
            modal.vm.$emit("close");
            await wrapper.vm.$nextTick();

            expect(wrapper.find("[data-description='workflow editor error modal']").props("show")).toBe(false);
        });
    });

    describe("onNavigate", () => {
        let navWrapper: Wrapper<IndexComponent>;

        /** Mounts a fresh Index instance on its own router, so route state (and
         * router.push call history) never leaks between these tests. */
        async function mountForNav(propsData: Record<string, unknown> = {}) {
            const testingPinia = createTestingPinia({ createSpy: vi.fn });
            setActivePinia(testingPinia);
            const datatypesStore = useDatatypesMapperStore();
            datatypesStore.datatypesMapper = testDatatypesMapper;

            const navLocalVue = getLocalVue();
            navLocalVue.use(PiniaVuePlugin);
            const navRouter = injectTestRouter(navLocalVue);

            const w = shallowMount(Index as object, {
                propsData: {
                    workflowId: "workflow_id",
                    initialVersion: 1,
                    workflowTags: [],
                    workflows: [],
                    toolbox: [],
                    ...propsData,
                },
                localVue: navLocalVue,
                pinia: testingPinia,
                router: navRouter,
                stubs: {
                    ActivityBar: {
                        template: "<div />",
                        methods: {
                            isActiveSideBar(name: string) {
                                return name === "workflow-editor-tools";
                            },
                        },
                        expose: ["isActiveSideBar"],
                    },
                    WorkflowGraph: {
                        template: "<div />",
                        methods: { fitWorkflow() {}, setTransform() {} },
                        expose: ["fitWorkflow", "setTransform"],
                    },
                },
            }) as Wrapper<IndexComponent>;
            await flushPromises();
            return w;
        }

        async function triggerHasChanges(w: Wrapper<IndexComponent>) {
            // Trigger hasChanges via the name watcher (see note above) rather than
            // mutating the store directly.
            w.vm.name = "trigger change";
            await w.vm.$nextTick();
            expect(w.vm.stateStore.hasChanges).toBeTruthy();
        }

        beforeEach(() => {
            mockSaveWorkflow.mockReset();
            mockSaveWorkflow.mockResolvedValue({ version: 1 });
        });

        it("navigates immediately when there are no unsaved changes", async () => {
            navWrapper = await mountForNav();
            const pushSpy = vi.spyOn(navWrapper.vm.$router, "push");

            await navWrapper.vm.onNavigate("/workflows/list");

            expect(navWrapper.findComponent(SaveChangesModal).props("showModal")).toBe(false);
            expect(mockSaveWorkflow).not.toHaveBeenCalled();
            expect(pushSpy).toHaveBeenCalledWith("/workflows/list");
        });

        it("shows the save-changes modal instead of navigating when there are unsaved changes", async () => {
            navWrapper = await mountForNav();
            const pushSpy = vi.spyOn(navWrapper.vm.$router, "push");
            await triggerHasChanges(navWrapper);

            await navWrapper.vm.onNavigate("/workflows/list");

            expect(pushSpy).not.toHaveBeenCalled();
            const modal = navWrapper.findComponent(SaveChangesModal);
            expect(modal.props("showModal")).toBe(true);
            expect(modal.props("navUrl")).toBe("/workflows/list");
        });

        it("does not navigate and keeps changes when the save-changes modal is cancelled", async () => {
            navWrapper = await mountForNav();
            const pushSpy = vi.spyOn(navWrapper.vm.$router, "push");
            await triggerHasChanges(navWrapper);
            await navWrapper.vm.onNavigate("/workflows/list");

            navWrapper.findComponent(SaveChangesModal).vm.$emit("update:show-modal", false);
            await navWrapper.vm.$nextTick();

            expect(pushSpy).not.toHaveBeenCalled();
            expect(mockSaveWorkflow).not.toHaveBeenCalled();
            expect(navWrapper.vm.stateStore.hasChanges).toBeTruthy();
            expect(navWrapper.findComponent(SaveChangesModal).props("showModal")).toBe(false);
        });

        it("navigates without saving when the save-changes modal's Don't Save is chosen", async () => {
            navWrapper = await mountForNav();
            const pushSpy = vi.spyOn(navWrapper.vm.$router, "push");
            await triggerHasChanges(navWrapper);
            await navWrapper.vm.onNavigate("/workflows/list");

            // "Don't Save": on-proceed emitted with forceSave=false, ignoreChanges=true
            navWrapper.findComponent(SaveChangesModal).vm.$emit("on-proceed", "/workflows/list", false, true, false);
            await flushPromises();

            expect(mockSaveWorkflow).not.toHaveBeenCalled();
            expect(pushSpy).toHaveBeenCalledWith("/workflows/list");
            expect(navWrapper.vm.stateStore.hasChanges).toBeFalsy();
        });

        it("saves before navigating when the save-changes modal's Save is chosen", async () => {
            navWrapper = await mountForNav();
            mockSaveWorkflow.mockResolvedValue({ version: 2 });
            const pushSpy = vi.spyOn(navWrapper.vm.$router, "push");
            await triggerHasChanges(navWrapper);
            await navWrapper.vm.onNavigate("/workflows/list");

            // "Save": on-proceed emitted with forceSave=true, ignoreChanges=false
            navWrapper.findComponent(SaveChangesModal).vm.$emit("on-proceed", "/workflows/list", true, false, false);
            await flushPromises();

            expect(mockSaveWorkflow).toHaveBeenCalled();
            expect(pushSpy).toHaveBeenCalledWith("/workflows/list");
            expect(navWrapper.vm.stateStore.hasChanges).toBeFalsy();
        });

        it("does not navigate if forced save fails", async () => {
            navWrapper = await mountForNav();
            mockSaveWorkflow.mockRejectedValue(new Error("boom"));
            const pushSpy = vi.spyOn(navWrapper.vm.$router, "push");
            await triggerHasChanges(navWrapper);

            await navWrapper.vm.onNavigate("/workflows/list", true);

            expect(mockSaveWorkflow).toHaveBeenCalled();
            expect(pushSpy).not.toHaveBeenCalled();
        });

        it("appends the current version to the URL when appendVersion is true", async () => {
            navWrapper = await mountForNav();
            const pushSpy = vi.spyOn(navWrapper.vm.$router, "push");

            await navWrapper.vm.onNavigate("/workflows/run?id=workflow_id", false, false, true);

            expect(pushSpy).toHaveBeenCalledWith(expect.stringContaining("&version="));
        });

        it("creates (rather than just saving) a new temp workflow when forced to save on navigate", async () => {
            // no workflowId prop => isNewTempWorkflow is true
            navWrapper = await mountForNav({ workflowId: undefined });
            const vm = navWrapper.vm;
            vm.services = {
                createWorkflow: vi
                    .fn()
                    .mockResolvedValue({ id: "new_id", name: "Unnamed Workflow", number_of_steps: 0 }),
            };
            const pushSpy = vi.spyOn(vm.$router, "push");
            mockSaveWorkflow.mockClear();

            await vm.onNavigate("/workflows/list", true);

            // onCreate() is used (not a plain onSave()) to persist the brand-new workflow;
            // onCreate() itself calls routeToWorkflow(), which does its own follow-up save
            // once the workflow has a real id, so saveWorkflow is expected to run after create.
            expect(vm.services.createWorkflow).toHaveBeenCalled();
            expect(pushSpy).toHaveBeenCalledWith("/workflows/list");
        });

        it("emits forceReload instead of pushing when navigating to the exact current route", async () => {
            navWrapper = await mountForNav();
            await navWrapper.vm.$router.push("/workflows/edit");
            const pushSpy = vi.spyOn(navWrapper.vm.$router, "push");

            await navWrapper.vm.onNavigate("/workflows/edit");

            expect(pushSpy).not.toHaveBeenCalled();
            expect(navWrapper.emitted().forceReload).toBeTruthy();
        });

        it("does not emit forceReload when navigating to a different route", async () => {
            navWrapper = await mountForNav();
            await navWrapper.vm.$router.push("/workflows/edit");

            await navWrapper.vm.onNavigate("/workflows/list");

            expect(navWrapper.emitted().forceReload).toBeFalsy();
        });

        it("createNewWorkflow routes through onNavigate and its unsaved-changes guard", async () => {
            navWrapper = await mountForNav();
            const onNavigateSpy = vi.spyOn(navWrapper.vm, "onNavigate");

            await navWrapper.vm.createNewWorkflow();

            expect(onNavigateSpy).toHaveBeenCalledWith("/workflows/edit");
        });
    });
});
