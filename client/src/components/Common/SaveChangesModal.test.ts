import { getLocalVue } from "@tests/vitest/helpers";
import { mount, type Wrapper } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type Vue from "vue";
import { nextTick } from "vue";

import SaveChangesModal from "./SaveChangesModal.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GModal from "@/components/BaseComponents/GModal.vue";

const mockOnBeforeRouteLeave = vi.fn();
const mockOnBeforeRouteUpdate = vi.fn();
const mockPush = vi.fn();
vi.mock("vue-router/composables", () => ({
    onBeforeRouteLeave: (guard: unknown) => mockOnBeforeRouteLeave(guard),
    onBeforeRouteUpdate: (guard: unknown) => mockOnBeforeRouteUpdate(guard),
    useRouter: vi.fn(() => ({
        push: mockPush,
    })),
}));

/** Simulates vue-router invoking a captured onBeforeRouteLeave/onBeforeRouteUpdate guard. */
function callGuard(mockRegister: typeof mockOnBeforeRouteLeave, toFullPath: string) {
    const guard = mockRegister.mock.calls[mockRegister.mock.calls.length - 1]?.[0] as (
        to: { fullPath: string },
        from: unknown,
        next: (arg?: false) => void,
    ) => void;
    const next = vi.fn();
    guard({ fullPath: toFullPath }, {}, next);
    return next;
}

const localVue = getLocalVue();

function footerButtons(wrapper: Wrapper<Vue>) {
    return wrapper.find(".save-changes-modal-button-container").findAllComponents(GButton).wrappers;
}

function buttonsDisabled(wrapper: Wrapper<Vue>) {
    return footerButtons(wrapper).map((button) => button.props("disabled"));
}

describe("SaveChangesModal reusable component", () => {
    let onSave: ReturnType<typeof vi.fn>;
    let onDiscard: ReturnType<typeof vi.fn>;
    let push: typeof mockPush;
    let wrapper: Wrapper<Vue>;

    beforeEach(() => {
        vi.clearAllMocks();
        onSave = vi.fn().mockResolvedValue(undefined);
        onDiscard = vi.fn();
        push = mockPush;
        push.mockResolvedValue(undefined);

        wrapper = mount(SaveChangesModal as object, {
            localVue,
            propsData: {
                hasChanges: false,
                onSave,
                onDiscard,
            },
        }) as Wrapper<Vue>;
    });

    afterEach(() => {
        wrapper.destroy();
    });

    async function makeDirty() {
        await wrapper.setProps({ hasChanges: true });
    }

    it("lets navigation through when there are no unsaved changes", () => {
        const next = callGuard(mockOnBeforeRouteLeave, "/pages/list");

        expect(next).toHaveBeenCalledWith();
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
    });

    it("blocks navigation and opens the modal when there are unsaved changes", async () => {
        await makeDirty();
        const next = callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        expect(next).toHaveBeenCalledWith(false);
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
    });

    it("blocks in-editor navigation (onBeforeRouteUpdate) the same way", async () => {
        await makeDirty();
        const next = callGuard(mockOnBeforeRouteUpdate, "/pages/editor?id=page-1&displayOnly=true");
        await nextTick();

        expect(next).toHaveBeenCalledWith(false);
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
    });

    it("Save proceeds: saves then navigates, closing the modal only once done", async () => {
        await makeDirty();
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await footerButtons(wrapper).at(2)!.vm.$emit("click");
        await flushPromises();

        expect(onSave).toHaveBeenCalled();
        expect(push).toHaveBeenCalledWith("/pages/list");
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
    });

    it("Don't Save proceeds: discards changes and navigates without saving", async () => {
        await makeDirty();
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await footerButtons(wrapper).at(1)!.vm.$emit("click");
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

        await footerButtons(wrapper).at(1)!.vm.$emit("click");
        await flushPromises();

        expect(push).toHaveBeenCalledWith("/pages/list");
    });

    it("Cancel: closes the modal and does not navigate", async () => {
        await makeDirty();
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await footerButtons(wrapper).at(0)!.vm.$emit("click");
        await flushPromises();

        expect(onSave).not.toHaveBeenCalled();
        expect(push).not.toHaveBeenCalled();
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);
    });

    it("Save fails: closes the modal (toasting the error) but keeps guarding the next navigation", async () => {
        await makeDirty();
        onSave.mockRejectedValueOnce(new Error("save failed"));
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await footerButtons(wrapper).at(2)!.vm.$emit("click");
        await flushPromises();

        expect(push).not.toHaveBeenCalled();
        expect(wrapper.findComponent(GModal).props("show")).toBe(false);

        // hasChanges is still true, so the guard must still be active: reopening the modal
        // on the next attempt, with buttons enabled (not stuck disabled from the failed try).
        const next = callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();
        expect(next).toHaveBeenCalledWith(false);
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
        expect(buttonsDisabled(wrapper)).toEqual([false, false, false]);
    });

    it("keeps guarding subsequent navigation, with buttons re-enabled, after a rejected router.push", async () => {
        await makeDirty();
        push.mockRejectedValueOnce(new Error("push failed"));
        callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        await footerButtons(wrapper).at(1)!.vm.$emit("click");
        await flushPromises();

        // bypassGuard must be reset even though the push rejected, so the next
        // navigation attempt is still protected instead of silently passing through.
        const next = callGuard(mockOnBeforeRouteLeave, "/pages/list");
        await nextTick();

        expect(next).toHaveBeenCalledWith(false);
        expect(wrapper.findComponent(GModal).props("show")).toBe(true);
        expect(buttonsDisabled(wrapper)).toEqual([false, false, false]);
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
            wrapper.destroy();
            const event = dispatchBeforeUnload();

            expect(event.defaultPrevented).toBe(false);
        });
    });
});
