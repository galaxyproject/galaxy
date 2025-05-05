import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { OK_PLUGIN_STATUS } from "@/components/ConfigTemplates/test_fixtures";
import { type ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";

import { type UserConcreteObjectStore } from "./types";

import CreateForm from "./CreateForm.vue";

const FAKE_OBJECT_STORE: UserConcreteObjectStore = {
    name: "My New Name",
    template_id: "moo",
    template_version: 0,
    active: true,
    badges: [],
    hidden: false,
    private: false,
    purged: false,
    quota: {
        enabled: false,
    },
    type: "aws_s3",
    uuid: "test_UUID",
    variables: {
        myvar: "default",
    },
    secrets: ["mysecret"],
};

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
            default: "default",
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
    hidden: false,
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
            default: "default",
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
    hidden: false,
};

const { server, http } = useServerMock();

describe("CreateForm", () => {
    it("should render a form with admin markdown converted to HTML in help", async () => {
        const wrapper = mount(CreateForm as object, {
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
        const wrapper = mount(CreateForm as object, {
            propsData: {
                template: SIMPLE_TEMPLATE,
            },
            localVue,
        });

        server.use(
            http.post("/api/object_store_instances", ({ response }) => {
                return response(200).json(FAKE_OBJECT_STORE);
            }),
            http.post("/api/object_store_instances/test", ({ response }) => {
                return response(200).json(OK_PLUGIN_STATUS);
            })
        );

        const nameForElement = wrapper.find("#form-element-_meta_name");
        await nameForElement.find("input").setValue("My New Name");
        const submitElement = wrapper.find("#submit");
        await submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(1);
        expect(emitted[0][0]).toMatchObject(FAKE_OBJECT_STORE);
    });

    it("should indicate an error on failure", async () => {
        const wrapper = mount(CreateForm as object, {
            propsData: {
                template: SIMPLE_TEMPLATE,
            },
            localVue,
        });
        server.use(
            http.post("/api/object_store_instances", ({ response }) => {
                return response("4XX").json({ err_msg: "Error creating this", err_code: 400 }, { status: 400 });
            }),
            http.post("/api/object_store_instances/test", ({ response }) => {
                return response(200).json(OK_PLUGIN_STATUS);
            })
        );

        await flushPromises();
        const nameForElement = wrapper.find("#form-element-_meta_name");
        nameForElement.find("input").setValue("My New Name");
        const submitElement = wrapper.find("#submit");
        expect(wrapper.find("[data-description='object-store-creation-error']").exists()).toBe(false);
        submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(0);
        const errorEl = wrapper.find("[data-description='object-store-creation-error']");
        expect(errorEl.exists()).toBe(true);
        expect(errorEl.html()).toContain("Error creating this");
    });
});
