import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import pageTemplate from "@/components/PageDisplay/pageTemplate.yml";
import { Toast } from "@/composables/toast";

import PageForm from "./PageForm.vue";

vi.mock("@/composables/toast", () => {
    const toastInstance = { success: vi.fn(), error: vi.fn() };
    return {
        Toast: toastInstance,
        useToast: () => toastInstance,
    };
});

const { server, http } = useServerMock();
const localVue = getLocalVue();

const mockPush = vi.fn();

vi.mock("vue-router/composables", () => ({
    useRouter: () => ({
        push: (...args) => mockPush(...args),
    }),
}));

function mountTarget(props = {}) {
    return mount(PageForm, {
        localVue,
        propsData: props,
        stubs: {
            FontAwesomeIcon: true,
            BButton: true,
            BAlert: true,
        },
        directives: {
            localize: () => {},
        },
    });
}

describe("PageForm.vue - Create mode", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders loading spinner when fetching report", async () => {
        server.use(
            http.get("/api/invocations/:invocation_id/report", ({ response }) =>
                response(200).json({
                    id: 42,
                    title: "Invoked Report Title",
                    invocation_markdown: "## Report Content",
                }),
            ),
        );
        server.use(
            http.post("/api/pages", async ({ request, response }) => {
                const body = await request.json();
                expect(body.title).toBe("Invoked Report Title");
                expect(body.slug).toBe("invocation-42");
                expect(body.annotation).toBe("");
                expect(body.content).toBe("## Report Content");
                return response(200).json({ id: "new-page-321" });
            }),
        );
        const wrapper = mountTarget({ mode: "create", invocationId: "42" });
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
        await flushPromises();
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
        expect(wrapper.find("#page-title").element.value).toBe("Invoked Report Title");
        expect(wrapper.find("#page-slug").element.value).toBe("invocation-42");
        await wrapper.find("#page-submit").trigger("click");
        await flushPromises();
        expect(mockPush).toHaveBeenCalledWith("/pages/editor?id=new-page-321");
    });

    it("shows error alert if fetching report fails", async () => {
        server.use(
            http.get("/api/invocations/:invocation_id/report", ({ response }) =>
                response(500).json({ err_msg: "Failed to fetch report" }),
            ),
        );
        const wrapper = mountTarget({ mode: "create", invocationId: "fail" });
        await flushPromises();
        const alert = wrapper.findComponent({ name: "BAlert" });
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Failed to fetch report");
    });

    it("submit button is disabled when required fields are missing", async () => {
        const wrapper = mountTarget({ mode: "create" });
        await flushPromises();
        expect(wrapper.find("#page-submit").classes()).toContain("g-disabled");
    });

    it("submits page creation with correct fields", async () => {
        server.use(
            http.post("/api/pages", async ({ request, response }) => {
                const body = await request.json();
                expect(body.title).toBe("My Title");
                expect(body.slug).toBe("my-title");
                expect(body.annotation).toBe("An annotation");
                expect(body.content).toBe(pageTemplate.content);
                return response(200).json({ id: "new-page-123" });
            }),
        );
        const wrapper = mountTarget({ mode: "create" });
        await flushPromises();
        await wrapper.find("#page-title").setValue("My Title");
        await wrapper.find("#page-slug").setValue("my-title");
        await wrapper.find("#page-annotation").setValue("An annotation");
        await wrapper.find("#page-submit").trigger("click");
        await flushPromises();
        expect(mockPush).toHaveBeenCalledWith("/pages/editor?id=new-page-123");
    });

    it("shows API error if creation fails", async () => {
        server.use(http.post("/api/pages", ({ response }) => response(400).json({ err_msg: "Creation failed" })));
        const wrapper = mountTarget({ mode: "create" });
        await flushPromises();
        await wrapper.find("#page-title").setValue("Some Title");
        await wrapper.find("#page-slug").setValue("some-title");
        await wrapper.find("#page-submit").trigger("click");
        await flushPromises();
        expect(Toast.error).toHaveBeenCalledWith("Creation failed", "Error Creating Page");
    });
});

describe("PageForm.vue - Edit mode", () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it("renders loading spinner and fetches page details", async () => {
        server.use(
            http.get("/api/pages/:id", ({ response }) =>
                response(200).json({
                    id: "123",
                    title: "Test Page",
                    slug: "test-page",
                    annotation: "Testing page edit",
                    content: "## Sample Content",
                }),
            ),
        );
        const wrapper = mountTarget({ mode: "edit", id: "123" });
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
        await flushPromises();
        expect(wrapper.find("#page-title").element.value).toBe("Test Page");
        expect(wrapper.find("#page-slug").element.value).toBe("test-page");
        expect(wrapper.find("#page-annotation").element.value).toBe("Testing page edit");
    });

    it("shows error alert if fetching page fails", async () => {
        server.use(http.get("/api/pages/:id", ({ response }) => response(500).json({ err_msg: "Page load failed" })));
        const wrapper = mountTarget({ mode: "edit", id: "error-id" });
        await flushPromises();
        const alert = wrapper.findComponent({ name: "BAlert" });
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Page load failed");
    });

    it("submit button is disabled when required fields are missing", async () => {
        const wrapper = mountTarget({ mode: "edit", id: "123" });
        await flushPromises();
        expect(wrapper.find("#page-submit").classes()).toContain("g-disabled");
    });

    it("submits page update with correct fields", async () => {
        server.use(
            http.put("/api/pages/:id", async ({ request, response }) => {
                const body = await request.json();
                expect(body.title).toBe("Updated Title");
                expect(body.slug).toBe("updated-title");
                expect(body.annotation).toBe("Updated annotation");
                return response(200).json({});
            }),
        );
        const wrapper = mountTarget({ mode: "edit", id: "456" });
        await flushPromises();
        await wrapper.find("#page-title").setValue("Updated Title");
        await wrapper.find("#page-slug").setValue("updated-title");
        await wrapper.find("#page-annotation").setValue("Updated annotation");
        await wrapper.find("#page-submit").trigger("click");
        await flushPromises();
        expect(mockPush).toHaveBeenCalledWith("/pages/list");
    });

    it("shows API error if update fails", async () => {
        server.use(http.put("/api/pages/:id", ({ response }) => response(400).json({ err_msg: "Update failed" })));
        const wrapper = mountTarget({ mode: "edit", id: "789" });
        await flushPromises();
        await wrapper.find("#page-title").setValue("Error Title");
        await wrapper.find("#page-slug").setValue("error-title");
        await wrapper.find("#page-submit").trigger("click");
        await flushPromises();
        expect(Toast.error).toHaveBeenCalledWith("Update failed", "Error Updating Page");
    });
});
