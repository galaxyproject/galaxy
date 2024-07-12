import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { PluginStatus } from "@/api/configTemplates";
import { mockFetcher } from "@/api/schema/__mocks__";
import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";

import CreateForm from "./CreateForm.vue";

jest.mock("@/api/schema");

const FAKE_OBJECT_STORE = "A fake object store";

const localVue = getLocalVue(true);

const STANDARD_TEMPLATE: ObjectStoreTemplateSummary = {
    type: "aws_s3",
    name: "moo",
    description: null,
    variables: [
        {
            name: "myvar",
            type: "string",
            help: "*myvar help*",
        },
    ],
    secrets: [
        {
            name: "mysecret",
            help: "**mysecret help**",
        },
    ],
    id: "moo",
    version: 0,
    badges: [],
};

const SIMPLE_TEMPLATE: ObjectStoreTemplateSummary = {
    type: "aws_s3",
    name: "moo",
    description: null,
    variables: [
        {
            name: "myvar",
            type: "string",
            help: "*myvar help*",
        },
    ],
    secrets: [
        {
            name: "mysecret",
            help: "**mysecret help**",
        },
    ],
    id: "moo",
    version: 0,
    badges: [],
};

const FAKE_PLUGIN_STATUS: PluginStatus = {
    template_definition: {
        state: "ok",
        message: "ok",
    },
    template_settings: {
        state: "ok",
        message: "ok",
    },
    connection: {
        state: "ok",
        message: "ok",
    },
};

describe("CreateForm", () => {
    it("should render a form with admin markdown converted to HTML in help", async () => {
        const wrapper = mount(CreateForm, {
            propsData: {
                template: STANDARD_TEMPLATE,
            },
            localVue,
        });
        await flushPromises();

        const varFormEl = wrapper.find("#form-element-myvar");
        expect(varFormEl).toBeTruthy();
        expect(varFormEl.html()).toContain("<em>myvar help</em>");

        const secretFormEl = wrapper.find("#form-element-mysecret");
        expect(secretFormEl).toBeTruthy();
        expect(secretFormEl.html()).toContain("<strong>mysecret help</strong>");
    });

    it("should post to create a new object store on submit", async () => {
        const wrapper = mount(CreateForm, {
            propsData: {
                template: SIMPLE_TEMPLATE,
            },
            localVue,
        });
        mockFetcher.path("/api/object_store_instances/test").method("post").mock({ data: FAKE_PLUGIN_STATUS });
        mockFetcher.path("/api/object_store_instances").method("post").mock({ data: FAKE_OBJECT_STORE });
        await flushPromises();
        const nameForElement = wrapper.find("#form-element-_meta_name");
        nameForElement.find("input").setValue("My New Name");
        const submitElement = wrapper.find("#submit");
        submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(1);
        expect(emitted[0][0]).toBe(FAKE_OBJECT_STORE);
    });

    it("should indicate an error on failure", async () => {
        const wrapper = mount(CreateForm, {
            propsData: {
                template: SIMPLE_TEMPLATE,
            },
            localVue,
        });
        mockFetcher.path("/api/object_store_instances/test").method("post").mock({ data: FAKE_PLUGIN_STATUS });
        mockFetcher
            .path("/api/object_store_instances")
            .method("post")
            .mock(() => {
                throw Error("Error creating this");
            });
        await flushPromises();
        const nameForElement = wrapper.find("#form-element-_meta_name");
        nameForElement.find("input").setValue("My New Name");
        const submitElement = wrapper.find("#submit");
        expect(wrapper.find(".object-store-instance-creation-error").exists()).toBe(false);
        submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(0);
        const errorEl = wrapper.find(".object-store-instance-creation-error");
        expect(errorEl.exists()).toBe(true);
        expect(errorEl.html()).toContain("Error creating this");
    });
});
