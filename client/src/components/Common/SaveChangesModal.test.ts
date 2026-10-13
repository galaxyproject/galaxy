import { composeStories } from "@storybook/vue3-vite";
import { getLocalVue, nth, withPlugins } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount, type VueWrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, disposePinia, getActivePinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, onTestFinished, vi } from "vitest";
import { nextTick } from "vue";
import type * as VueRouter from "vue-router";

import { useToast } from "@/composables/toast";

import * as SaveChangesModalStories from "./SaveChangesModal.stories";

import SaveChangesModal from "./SaveChangesModal.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

// The component guard reads only fullPath and ignores from; retain the original partial routes.
type CapturedGuard = (
    to: Pick<Parameters<VueRouter.NavigationGuard>[0], "fullPath">,
    from: unknown,
    next: (arg?: false) => void,
) => ReturnType<VueRouter.NavigationGuard>;
type GuardRegistration = (guard: CapturedGuard) => void;
const mockOnBeforeRouteLeave = vi.fn<GuardRegistration>();
const mockOnBeforeRouteUpdate = vi.fn<GuardRegistration>();
const mockPush = vi.fn<VueRouter.Router["push"]>();
vi.mock("vue-router", async (importOriginal) => ({
    ...(await importOriginal<typeof VueRouter>()),
    onBeforeRouteLeave: (guard: CapturedGuard) => mockOnBeforeRouteLeave(guard),
    onBeforeRouteUpdate: (guard: CapturedGuard) => mockOnBeforeRouteUpdate(guard),
    useRouter: vi.fn(() => ({
        push: mockPush,
    })),
}));

/** Simulates vue-router invoking a captured onBeforeRouteLeave/onBeforeRouteUpdate guard. */
function callGuard(mockRegister: typeof mockOnBeforeRouteLeave, toFullPath: string) {
    const [guard] = nth(mockRegister.mock.calls, -1);
    const next = vi.fn<(arg?: false) => void>();
    guard({ fullPath: toFullPath }, {}, next);
    return next;
}

const stories = composeStories(SaveChangesModalStories);
const mountStory = useStoryMount();
const localVue = getLocalVue();

function mountModal(onSave: () => Promise<unknown>, onDiscard: () => void) {
    const pinia = createPinia();
    onTestFinished(() => {
        disposePinia(pinia);
        if (getActivePinia() === pinia) {
            setActivePinia(undefined);
        }
    });
    return mount(SaveChangesModal, {
        global: withPlugins(localVue, pinia),
        props: { hasChanges: false, onSave, onDiscard },
    });
}

type ModalWrapper = ReturnType<typeof mountModal>;

function footerButtons(wrapper: ModalWrapper): VueWrapper<InstanceType<typeof GButton>>[] {
    return wrapper.get(".save-changes-modal-button-container").findAllComponents(GButton);
}

function buttonsDisabled(wrapper: ModalWrapper) {
    return footerButtons(wrapper).map((button) => button.props("disabled"));
}

describe("Saved page story", () => {
    beforeEach(() => vi.clearAllMocks());

    it("lets navigation through when there are no unsaved changes", () => {
        const wrapper = mountStory(stories.SavedPage).getComponent(SaveChangesModal);
        const next = callGuard(mockOnBeforeRouteLeave, "/pages/list");

        expect(next).toHaveBeenCalledWith();
        expect(wrapper.getComponent(GModal).props("show")).toBe(false);
    });
});

describe("SaveChangesModal reusable component", () => {
    let onSave: ReturnType<typeof vi.fn<() => Promise<unknown>>>;
    let onDiscard: ReturnType<typeof vi.fn<() => void>>;
    let push: typeof mockPush;
    let wrapper: ModalWrapper;

    beforeEach(() => {
        const toast = useToast();
        const existingToastIds = new Set(toast.toasts.value.map((item) => item.id));
        onTestFinished(() => {
            for (const item of [...toast.toasts.value]) {
                if (!existingToastIds.has(item.id)) {
                    toast.removeToast(item.id);
                }
            }
        });
        vi.clearAllMocks();
        onSave = vi.fn<() => Promise<unknown>>().mockResolvedValue(undefined);
        onDiscard = vi.fn<() => void>();
        push = mockPush;
        push.mockReset().mockResolvedValue(undefined);

        wrapper = mountModal(onSave, onDiscard);
    });

    enableAutoUnmount(afterEach);

    async function makeDirty() {
        await wrapper.setProps({ hasChanges: true });
    }

    it("blocks navigation and opens the modal when there are unsaved changes", async () => {
        await makeDirty();
        const next = callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        expect(next).toHaveBeenCalledWith(false);
        expect(wrapper.getComponent(GModal).props("show")).toBe(true);
    });

    it("blocks in-editor navigation (onBeforeRouteUpdate) the same way", async () => {
        await makeDirty();
        const next = callGuard(mockOnBeforeRouteUpdate, "/pages/editor?id=page-1&displayOnly=true");
        await nextTick();

        expect(next).toHaveBeenCalledWith(false);
        expect(wrapper.getComponent(GModal).props("show")).toBe(true);
    });

    it("Save proceeds: saves then navigates, closing the modal only once done", async () => {
        await makeDirty();
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await nth(footerButtons(wrapper), 2).vm.$emit("click");
        await flushPromises();

        expect(onSave).toHaveBeenCalled();
        expect(push).toHaveBeenCalledWith("/pages/list");
        expect(wrapper.getComponent(GModal).props("show")).toBe(false);
    });

    it("Don't Save proceeds: discards changes and navigates without saving", async () => {
        await makeDirty();
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await nth(footerButtons(wrapper), 1).vm.$emit("click");
        await flushPromises();

        expect(onSave).not.toHaveBeenCalled();
        expect(onDiscard).toHaveBeenCalled();
        expect(push).toHaveBeenCalledWith("/pages/list");
    });

    it("Don't Save without an onDiscard still navigates", async () => {
        await wrapper.setProps({ onDiscard: undefined });
        await makeDirty();
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await nth(footerButtons(wrapper), 1).vm.$emit("click");
        await flushPromises();

        expect(push).toHaveBeenCalledWith("/pages/list");
    });

    it("Cancel: closes the modal and does not navigate", async () => {
        await makeDirty();
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await nth(footerButtons(wrapper), 0).vm.$emit("click");
        await flushPromises();

        expect(onSave).not.toHaveBeenCalled();
        expect(push).not.toHaveBeenCalled();
        expect(wrapper.getComponent(GModal).props("show")).toBe(false);
    });

    it("Save fails: closes the modal (toasting the error) but keeps guarding the next navigation", async () => {
        await makeDirty();
        onSave.mockRejectedValueOnce(new Error("save failed"));
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await nth(footerButtons(wrapper), 2).vm.$emit("click");
        await flushPromises();

        expect(push).not.toHaveBeenCalled();
        expect(wrapper.getComponent(GModal).props("show")).toBe(false);

        // hasChanges is still true, so the guard must still be active: reopening the modal
        // on the next attempt, with buttons enabled (not stuck disabled from the failed try).
        const next = callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();
        expect(next).toHaveBeenCalledWith(false);
        expect(wrapper.getComponent(GModal).props("show")).toBe(true);
        expect(buttonsDisabled(wrapper)).toEqual([false, false, false]);
    });

    it("keeps guarding subsequent navigation, with buttons re-enabled, after a rejected router.push", async () => {
        await makeDirty();
        push.mockRejectedValueOnce(new Error("push failed"));
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await nth(footerButtons(wrapper), 1).vm.$emit("click");
        await flushPromises();

        // bypassGuard must be reset even though the push rejected, so the next
        // navigation attempt is still protected instead of silently passing through.
        const next = callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        expect(next).toHaveBeenCalledWith(false);
        expect(wrapper.getComponent(GModal).props("show")).toBe(true);
        expect(buttonsDisabled(wrapper)).toEqual([false, false, false]);
    });

    describe("guardNavigation", () => {
        it("runs a navigation the router cannot see straight away when there is nothing to lose", () => {
            const navigate = vi.fn();

            wrapper.vm.guardNavigation(navigate);

            expect(navigate).toHaveBeenCalled();
            expect(wrapper.getComponent(GModal).props("show")).toBe(false);
        });

        it("prompts first when there are changes, then runs it once saved", async () => {
            const navigate = vi.fn();
            await makeDirty();

            wrapper.vm.guardNavigation(navigate);
            await nextTick();

            expect(navigate).not.toHaveBeenCalled();
            expect(wrapper.getComponent(GModal).props("show")).toBe(true);

            await nth(footerButtons(wrapper), 2).vm.$emit("click");
            await flushPromises();

            expect(onSave).toHaveBeenCalled();
            expect(navigate).toHaveBeenCalled();
            // It is not a route change, so nothing should have been pushed.
            expect(push).not.toHaveBeenCalled();
        });

        it("discards and runs it on Don't Save", async () => {
            const navigate = vi.fn();
            await makeDirty();

            wrapper.vm.guardNavigation(navigate);
            await nextTick();
            await nth(footerButtons(wrapper), 1).vm.$emit("click");
            await flushPromises();

            expect(onSave).not.toHaveBeenCalled();
            expect(onDiscard).toHaveBeenCalled();
            expect(navigate).toHaveBeenCalled();
        });

        it("drops it on Cancel", async () => {
            const navigate = vi.fn();
            await makeDirty();

            wrapper.vm.guardNavigation(navigate);
            await nextTick();
            await nth(footerButtons(wrapper), 0).vm.$emit("click");
            await flushPromises();

            expect(navigate).not.toHaveBeenCalled();
            expect(wrapper.getComponent(GModal).props("show")).toBe(false);
        });
    });

    describe("beforeunload", () => {
        function dispatchBeforeUnload() {
            const event = new Event("beforeunload", { cancelable: true }) as BeforeUnloadEvent;
            window.dispatchEvent(event);
            return event;
        }

        it("does not prevent unload when there are no unsaved changes", () => {
            const event = dispatchBeforeUnload();

            expect(event.defaultPrevented).toBe(false);
        });

        it("prevents unload when there are unsaved changes", async () => {
            await makeDirty();
            const event = dispatchBeforeUnload();

            expect(event.defaultPrevented).toBe(true);
        });

        it("stops listening after unmount", async () => {
            await makeDirty();
            wrapper.unmount();
            const event = dispatchBeforeUnload();

            expect(event.defaultPrevented).toBe(false);
        });
    });
});
