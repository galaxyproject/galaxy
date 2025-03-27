import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import pageTemplate from "@/components/PageDisplay/pageTemplate.yml";

import PageCreate from "./PageCreate.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue();

const mockPush = jest.fn();

jest.mock("vue-router/composables", () => ({
    useRoute: jest.fn(() => ({})),
    useRouter: jest.fn(() => ({
        push: (...args) => mockPush(...args),
    })),
}));

function mountTarget(props = {}) {
    return mount(PageCreate, {
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

describe("PageCreate.vue", () => {
    it("renders loading spinner initially when fetching report", async () => {
        server.use(
            http.get("/api/invocations/:invocation_id/report", ({ response }) =>
                response(200).json({
                    id: 42,
                    title: "Invoked Report Title",
                    invocation_markdown: "## Report Content",
                })
            )
        );
        server.use(
            http.post("/api/pages", async ({ request, response }) => {
                const body = await request.json();
                const { title, slug, content, annotation } = body;
                expect(title).toBe("Invoked Report Title");
                expect(slug).toBe("invocation-42");
                expect(annotation).toBe("");
                expect(content).toBe("## Report Content");
                return response(200).json({ id: "new-page-321" });
            })
        );
        const wrapper = mountTarget({ invocationId: "42" });
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(true);
        await flushPromises();
        expect(wrapper.findComponent({ name: "LoadingSpan" }).exists()).toBe(false);
        expect(wrapper.find("input#page-title").element.value).toBe("Invoked Report Title");
        expect(wrapper.find("input#page-slug").element.value).toBe("invocation-42");
        await wrapper.findComponent({ name: "BButton" }).trigger("click");
        await flushPromises();
        expect(mockPush).toHaveBeenCalledWith("/pages/editor?id=new-page-321");
    });

    it("shows error alert when fetching report fails", async () => {
        server.use(
            http.get("/api/invocations/:invocation_id/report", ({ response }) =>
                response(500).json({ err_msg: "Failed to fetch report" })
            )
        );
        const wrapper = mountTarget({ invocationId: "fail" });
        await flushPromises();
        const alert = wrapper.findComponent({ name: "BAlert" });
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Failed to fetch report");
    });

    it("shows validation error if required fields are missing on submit", async () => {
        const wrapper = mountTarget();
        await wrapper.findComponent({ name: "BButton" }).trigger("click");
        await flushPromises();
        const alert = wrapper.findComponent({ name: "BAlert" });
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Please complete all required inputs.");
    });

    it("submits page creation when title and slug are present", async () => {
        server.use(
            http.post("/api/pages", async ({ request, response }) => {
                const body = await request.json();
                const { title, slug, content, annotation } = body;
                expect(title).toBe("My Title");
                expect(slug).toBe("my-title");
                expect(annotation).toBe("An annotation");
                expect(content).toBe(pageTemplate.content);
                return response(200).json({ id: "new-page-123" });
            })
        );
        const wrapper = mountTarget();
        await wrapper.find("#page-title").setValue("My Title");
        await wrapper.find("#page-slug").setValue("my-title");
        await wrapper.find("#page-annotation").setValue("An annotation");
        await wrapper.findComponent({ name: "BButton" }).trigger("click");
        await flushPromises();
        expect(mockPush).toHaveBeenCalledWith("/pages/editor?id=new-page-123");
    });

    it("shows API error if creation fails", async () => {
        server.use(http.post("/api/pages", ({ response }) => response(400).json({ err_msg: "Creation failed" })));
        const wrapper = mountTarget();
        await wrapper.find("#page-title").setValue("Some Title");
        await wrapper.find("#page-slug").setValue("some-title");
        await wrapper.findComponent({ name: "BButton" }).trigger("click");
        await flushPromises();
        const alert = wrapper.findComponent({ name: "BAlert" });
        expect(alert.exists()).toBe(true);
        expect(alert.text()).toContain("Creation failed");
    });
});
