import "@tests/vitest/mockHelpPopovers";

import { getFakeRegisteredUser } from "@tests/test-data";
import { getLocalVue, injectTestRouter } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { createPinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { HttpResponse, useServerMock } from "@/api/client/__mocks__";
import MockCurrentHistory from "@/components/providers/MockCurrentHistory";
import { useHistoryStore } from "@/stores/historyStore";
import { useUserStore } from "@/stores/userStore";

import ToolForm from "./ToolForm.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue();
const router = injectTestRouter(localVue);
const pinia = createPinia();

vi.mock("@/composables/userLocalStorageFromHashedId", async () => {
    const { ref } = await import("vue");
    return {
        useUserLocalStorageFromHashId: (_key, initialValue) => ref(initialValue),
    };
});

describe("ToolForm", () => {
    let wrapper;
    let userStore;
    let historyStore;

    beforeEach(() => {
        // I tried using the useConfig mock and this component seems to bypass that, it would be
        // better if it didn't. We shouldn't have to stub out an API request to get a particular config.
        server.use(
            http.get("/api/configuration", ({ response }) => {
                return response.untyped(
                    HttpResponse.json({
                        enable_tool_source_display: false,
                        object_store_allows_id_selection: false,
                    }),
                );
            }),
            http.untyped.get("/api/tools/tool_id/build", ({ request }) => {
                const url = new URL(request.url);
                if (url.searchParams.get("tool_version") === "version") {
                    return HttpResponse.json({
                        id: "tool_id",
                        name: "tool_name",
                        version: "version",
                        inputs: [],
                        help: "help_text",
                        help_format: "restructuredtext",
                        creator: [
                            { class: "Person", givenName: "FakeName", familyName: "FakeSurname", email: "fakeEmail" },
                        ],
                    });
                }
                return HttpResponse.json({});
            }),
            http.untyped.get("/api/webhooks", () => {
                return HttpResponse.json([]);
            }),
            http.untyped.get("/api/tools/tool_id/citations", () => {
                return HttpResponse.json([]);
            }),
        );

        wrapper = mount(ToolForm, {
            propsData: {
                id: "tool_id",
                version: "version",
            },
            localVue,
            router,
            stubs: {
                UserHistories: MockCurrentHistory({ id: "fakeHistory" }),
                FormDisplay: true,
            },
            pinia,
        });
        userStore = useUserStore();
        userStore.currentUser = getFakeRegisteredUser({ id: "fakeUser" });

        historyStore = useHistoryStore();
        historyStore.setHistories([{ id: "fakeHistory" }]);
        historyStore.setCurrentHistoryId("fakeHistory");
        historyStore.startWatchingHistory = () => {};
    });

    it("shows props", async () => {
        await flushPromises();
        const button = wrapper.find("[data-description='run tool button']");
        expect(button.attributes("data-title")).toBe("Run tool: tool_name (version)");
        const dropdown = wrapper.findAll(".dropdown-item");
        expect(dropdown.length).toBe(2);
        const noToolParametersAlert = wrapper.find("[data-description='no tool parameters']");
        expect(noToolParametersAlert.text()).toContain("This tool requires no input parameters and can be run as is.");
        const help = wrapper.find(".form-help");
        expect(help.text()).toBe("help_text");
        const creator = wrapper.find(".creative-work-creator");
        expect(creator.text()).toContain("FakeName FakeSurname");
    });

    it("adds the executed tool to recent tools", async () => {
        await flushPromises();
        await wrapper.setData({ formData: {} });

        const button = wrapper.find("[data-description='run tool button']");
        await button.trigger("click");
        await flushPromises();

        expect(userStore.recentTools).toEqual(["tool_id"]);
    });

    it("preserves client-side validation errors on input change (does not wipe formConfig.errors when only validationInternal is set)", async () => {
        await flushPromises();
        // Simulate steady state: no backend errors, but a client-side validation error
        // raised by FormDisplay (e.g. a required field was cleared).
        await wrapper.setData({
            formConfigInitialized: true,
            validationInternal: ["multi_required", "Please provide a value for this option."],
        });
        wrapper.vm.formConfig.errors = {};

        wrapper.vm.onChange({ multi_required: null }, false);

        // Should NOT have been assigned null — that would cascade through props.errors
        // and wipe the client-side validation error before it can render.
        expect(wrapper.vm.formConfig.errors).toEqual({});
    });

    it("still wipes formConfig.errors when there are actual backend errors to clear on input change", async () => {
        await flushPromises();
        await wrapper.setData({ formConfigInitialized: true });
        wrapper.vm.formConfig.errors = { multi_required: "Backend rejected this value." };

        wrapper.vm.onChange({ multi_required: "alpha" }, false);

        expect(wrapper.vm.formConfig.errors).toBeNull();
    });

    it("shows an error alert when tool submission returns an error message", async () => {
        const errorMessage = "New identifier [duplicate] appears twice in resulting collection.";
        server.use(
            http.untyped.post("/api/tools", () => {
                return HttpResponse.json({ err_msg: errorMessage }, { status: 400 });
            }),
        );
        await flushPromises();
        await wrapper.setData({ formData: {} });

        const button = wrapper.find("[data-description='run tool button']");
        await button.trigger("click");
        await flushPromises();

        expect(wrapper.vm.showError).toBe(true);
        expect(wrapper.vm.errorMessage).toBe(errorMessage);
        expect(wrapper.text()).toContain(errorMessage);
    });
});
