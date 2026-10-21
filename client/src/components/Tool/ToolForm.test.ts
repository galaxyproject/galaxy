import "@tests/vitest/mockHelpPopovers";

import { composeStories } from "@storybook/vue3-vite";
import { getFakeHistorySummary, getFakeRegisteredUser } from "@tests/test-data";
import { getFakeToolFormConfig } from "@tests/test-data/tools";
import { deferred } from "@tests/vitest/deferred";
import { createTestRouter, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia, disposePinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import MockCurrentHistory from "@/components/providers/MockCurrentHistory";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { seedCurrentHistory } from "@/stores/testUtils";
import { useUserStore } from "@/stores/userStore";

import * as componentStories from "./ToolForm.stories";

import ToolCard from "./ToolCard.vue";
import ToolForm from "./ToolForm.vue";
import FormDisplay from "@/components/Form/FormDisplay.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue();
const stories = composeStories(componentStories);
const mountStory = useStoryMount();

vi.mock("@/composables/userLocalStorageFromHashedId", async () => {
    const { ref } = await import("vue");
    return {
        useUserLocalStorageFromHashId: (_key: string, initialValue: unknown) => ref(initialValue),
    };
});

describe("ToolForm", () => {
    // Components must unmount before their stores are disposed.
    let disposeStores: (() => void) | undefined;
    afterEach(() => {
        disposeStores?.();
        disposeStores = undefined;
        useToast().clearToasts();
    });
    enableAutoUnmount(afterEach);

    // Keep the initial provider-arrival case: story decorators preload user and history.
    async function mountInitialToolForm() {
        const pinia = createPinia();
        // Select this Pinia before lookup: a testing Pinia otherwise overrides the explicit argument.
        setActivePinia(pinia);
        disposeStores = () => disposePinia(pinia);
        const userStore = useUserStore(pinia);
        const history = getFakeHistorySummary({ id: "fakeHistory" });
        const wrapper = mount(ToolForm, {
            props: {
                id: "tool_id",
                version: "version",
            },
            global: {
                ...withPlugins(localVue, pinia, createTestRouter()),
                stubs: {
                    ...localVue.stubs,
                    UserHistories: MockCurrentHistory(history),
                    FormDisplay: true,
                },
            },
        });
        // Exercise the initial loading state before the current user and history arrive.
        userStore.currentUser = getFakeRegisteredUser({ id: "fakeUser" });
        const historyStore = useHistoryStore(pinia);
        historyStore.setHistories([history]);
        seedCurrentHistory(history, pinia);
        await nextTick();
        vi.spyOn(historyStore, "startWatchingHistory").mockImplementation(() => {});
        await flushPromises();
        await vi.waitFor(() => expect(wrapper.find("[data-description='run tool button']").exists()).toBe(true));
        return { wrapper, userStore };
    }

    async function mountToolForm() {
        const outer = mountStory(stories.NoInputParameters, {
            props: { id: "tool_id", version: "version" },
            global: { stubs: { FormDisplay: true } },
        });
        const userStore = useUserStore();
        vi.spyOn(useHistoryStore(), "startWatchingHistory").mockImplementation(() => {});
        await flushPromises();
        return { wrapper: outer.getComponent(ToolForm), userStore };
    }

    function buildResponse(overrides = {}) {
        return {
            ...getFakeToolFormConfig(),
            id: "tool_id",
            name: "tool_name",
            version: "version",
            inputs: [],
            help: "help_text",
            help_format: "restructuredtext",
            creator: [{ class: "Person", givenName: "FakeName", familyName: "FakeSurname", email: "fakeEmail" }],
            ...overrides,
        };
    }

    function useBuildResponse(overrides = {}) {
        server.use(
            http.untyped.get("/api/tools/tool_id/build", ({ request }) => {
                const url = new URL(request.url);
                if (url.searchParams.get("tool_version") === "version") {
                    return HttpResponse.json(buildResponse(overrides));
                }
                return HttpResponse.json({});
            }),
        );
    }

    beforeEach(() => {
        // Reuse the same configuration, webhooks and citations seams for the provider-arrival mount.
        server.use(...Object.values(componentStories.default.parameters.msw.handlers));

        useBuildResponse();
        useToast().clearToasts();
    });

    it("shows the tool title, available actions, empty-input message, help, and creator", async () => {
        const { wrapper } = await mountInitialToolForm();
        const button = wrapper.get("[data-description='run tool button']");
        expect(button.attributes("data-title")).toBe("Run tool: tool_name (version)");
        const dropdown = wrapper.findAll(".dropdown-item");
        expect(dropdown.length).toBe(2);
        const noToolParametersAlert = wrapper.get("[data-description='no tool parameters']");
        expect(noToolParametersAlert.text()).toContain("This tool requires no input parameters and can be run as is.");
        const help = wrapper.get(".form-help");
        expect(help.text()).toBe("help_text");
        const creator = wrapper.get(".creative-work-creator");
        expect(creator.text()).toContain("FakeName FakeSurname");
    });

    it("adds the executed tool to recent tools", async () => {
        const { wrapper, userStore } = await mountToolForm();
        wrapper.getComponent(FormDisplay).vm.$emit("onChange", {}, false);

        const button = wrapper.get("[data-description='run tool button']");
        await button.trigger("click");
        await flushPromises();

        expect(userStore.recentTools).toEqual(["tool_id"]);
    });

    it("moves an already recent tool to the front without duplicating it", async () => {
        const { wrapper, userStore } = await mountToolForm();
        userStore.recentTools = ["previous_tool", "tool_id"];
        wrapper.getComponent(FormDisplay).vm.$emit("onChange", {}, false);
        await wrapper.get("[data-description='run tool button']").trigger("click");
        await flushPromises();

        expect(userStore.recentTools).toEqual(["tool_id", "previous_tool"]);
    });

    it("shows loading while the tool build is pending for an existing history", async () => {
        const build = deferred<ReturnType<typeof buildResponse>>();
        server.use(http.untyped.get("/api/tools/tool_id/build", async () => HttpResponse.json(await build.promise)));
        try {
            const { wrapper } = await mountToolForm();
            expect(wrapper.get("[data-description='loading message']").text()).toBe("Loading Tool...");
            build.resolve(buildResponse());
            await flushPromises();
            expect(wrapper.get("[data-description='run tool button']").attributes("data-title")).toBe(
                "Run tool: tool_name (version)",
            );
        } finally {
            build.resolve(buildResponse());
            await flushPromises();
        }
    });

    it("preserves client-side validation errors when input changes without backend errors", async () => {
        useBuildResponse({ errors: {} });
        const { wrapper } = await mountToolForm();

        const formDisplay = wrapper.getComponent(FormDisplay);
        // Simulate steady state: no backend errors, but a client-side validation error
        // raised by FormDisplay (e.g. a required field was cleared).
        await formDisplay.vm.$emit("onValidation", ["multi_required", "Please provide a value for this option."]);
        // First onChange sets formConfigInitialized; second is the one under test.
        await formDisplay.vm.$emit("onChange", { multi_required: null }, false);
        await formDisplay.vm.$emit("onChange", { multi_required: null }, false);

        // Should NOT have been assigned null — that would cascade through props.errors
        // and wipe the client-side validation error before it can render.
        expect(formDisplay.props("errors")).toEqual({});
    });

    it("clears backend validation errors when input changes", async () => {
        useBuildResponse({ errors: { multi_required: "Backend rejected this value." } });
        const { wrapper } = await mountToolForm();

        const formDisplay = wrapper.getComponent(FormDisplay);
        // First onChange sets formConfigInitialized; second triggers the wipe.
        await formDisplay.vm.$emit("onChange", { multi_required: "alpha" }, false);
        await formDisplay.vm.$emit("onChange", { multi_required: "alpha" }, false);

        expect(formDisplay.props("errors")).toBeNull();
    });

    it("shows an error alert when tool submission returns an error message", async () => {
        // Preserve the original synthetic rejection; standalone stories use shipped tool models.
        const errorMessage = "New identifier [duplicate] appears twice in resulting collection.";
        server.use(
            http.untyped.post("/api/tools", () => {
                return HttpResponse.json({ err_msg: errorMessage }, { status: 400 });
            }),
        );
        const { wrapper } = await mountToolForm();
        wrapper.getComponent(FormDisplay).vm.$emit("onChange", {}, false);

        const button = wrapper.get("[data-description='run tool button']");
        await button.trigger("click");
        await flushPromises();

        expect(wrapper.text()).toContain(errorMessage);
    });

    it("reports a rejected form update and re-enables the form", async () => {
        const { toasts, clearToasts } = useToast();
        clearToasts();
        // Test-local 429 checks recovery independently of the endpoint's actual error statuses.
        server.use(
            http.untyped.post("/api/tools/tool_id/build", () => {
                return HttpResponse.json({ err_msg: "Rate limit exceeded" }, { status: 429 });
            }),
        );
        const { wrapper } = await mountToolForm();

        wrapper.getComponent(FormDisplay).vm.$emit("onChange", {}, true);
        await flushPromises();

        expect(toasts.value).toEqual([
            expect.objectContaining({
                message: "Rate limit exceeded",
                title: "Updating parameters failed",
                variant: "danger",
            }),
        ]);
        expect(wrapper.getComponent(ToolCard).props("disabled")).toBe(false);
        clearToasts();
    });
});
