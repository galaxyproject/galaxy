import { getFakeObjectStoreInstance } from "@tests/test-data/objectStores";
import { getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { OK_PLUGIN_STATUS } from "@/components/ConfigTemplates/test_fixtures";
import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";

import CreateForm from "./CreateForm.vue";

const FAKE_OBJECT_STORE = getFakeObjectStoreInstance({
    name: "My New Name",
    template_id: "moo",
    uuid: "test_UUID",
    variables: { myvar: "default" },
    secrets: ["mysecret"],
});

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

const OPTIONAL_SECRET_TEMPLATE: ObjectStoreTemplateSummary = {
    type: "aws_s3",
    name: "moo",
    description: null,
    variables: [
        {
            name: "myvar",
            type: "string",
            help: "myvar help",
            default: "default",
        },
    ],
    secrets: [
        {
            name: "optional_secret",
            help: "An optional secret",
            optional: true,
        },
    ],
    id: "moo",
    version: 0,
    badges: [],
    hidden: false,
};

const OPTIONAL_VAR_WITH_VALIDATION_TEMPLATE: ObjectStoreTemplateSummary = {
    type: "aws_s3",
    name: "moo",
    description: null,
    variables: [
        {
            name: "optional_var",
            type: "string",
            help: "optional var help",
            default: "",
            optional: true,
            validators: [
                {
                    type: "length",
                    min: 5,
                    message: "Must be at least 5 characters",
                    negate: false,
                    implicit: false,
                },
            ],
        },
    ],
    secrets: [
        {
            name: "mysecret",
            help: "mysecret help",
            optional: true,
        },
    ],
    id: "moo",
    version: 0,
    badges: [],
    hidden: false,
};

enableAutoUnmount(afterEach);
const { server, http } = useServerMock();

function mountCreateForm(template: ObjectStoreTemplateSummary) {
    // Real fields are needed to cover help rendering, validation, and submission.
    return mount(CreateForm as object, {
        props: { template: structuredClone(template) },
        global: getLocalVue(true),
    });
}

describe("CreateForm", () => {
    it("renders admin Markdown as HTML in variable and secret help", async () => {
        const wrapper = mountCreateForm(STANDARD_TEMPLATE);
        await flushPromises();

        const varFormEl = wrapper.find("#form-element-myvar");
        expect(varFormEl.exists()).toBe(true);
        expect(varFormEl.html()).toContain("<em>myvar help</em>");

        const secretFormEl = wrapper.find("#form-element-mysecret");
        expect(secretFormEl.exists()).toBe(true);
        expect(secretFormEl.html()).toContain("<strong>mysecret help</strong>");
    });

    it("emits the created object store after successful submission", async () => {
        const wrapper = mountCreateForm(STANDARD_TEMPLATE);

        server.use(
            http.post("/api/object_store_instances", ({ response }) => {
                return response(200).json(FAKE_OBJECT_STORE);
            }),
            http.post("/api/object_store_instances/test", ({ response }) => {
                return response(200).json(OK_PLUGIN_STATUS);
            }),
        );

        const nameForElement = wrapper.find("#form-element-_meta_name");
        await nameForElement.find("input").setValue("My New Name");

        const passwordElement = wrapper.find("#form-element-mysecret");
        await passwordElement.find("input").setValue("mysecretvalue");

        const submitElement = wrapper.find("#submit");
        await submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(1);
        expect(emitted).toEqual([[FAKE_OBJECT_STORE]]);
    });

    it("shows the creation error and emits no object store when submission fails", async () => {
        const wrapper = mountCreateForm(STANDARD_TEMPLATE);
        server.use(
            http.post("/api/object_store_instances", ({ response }) => {
                return response("4XX").json({ err_msg: "Error creating this", err_code: 400 }, { status: 400 });
            }),
            http.post("/api/object_store_instances/test", ({ response }) => {
                return response(200).json(OK_PLUGIN_STATUS);
            }),
        );

        await flushPromises();
        const nameForElement = wrapper.find("#form-element-_meta_name");
        await nameForElement.find("input").setValue("My New Name");

        const passwordElement = wrapper.find("#form-element-mysecret");
        await passwordElement.find("input").setValue("mysecretvalue");

        expect(wrapper.find("[data-description='object-store-creation-error']").exists()).toBe(false);

        const submitElement = wrapper.find("#submit");
        await submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(0);
        const errorEl = wrapper.find("[data-description='object-store-creation-error']");
        expect(errorEl.exists()).toBe(true);
        expect(errorEl.text()).toContain("Error creating this");
    });

    it("disables submission when a required secret is empty", async () => {
        const wrapper = mountCreateForm(STANDARD_TEMPLATE);

        const nameForElement = wrapper.find("#form-element-_meta_name");
        await nameForElement.find("input").setValue("My New Name");

        // Leave secret empty to trigger validation error

        const submitElement = wrapper.find("#submit");
        expect(submitElement.classes()).toContain("g-disabled");

        // Try to click when submit is disabled will not emit created event
        await submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(0);
    });

    it("allows submission when an optional secret is empty", async () => {
        server.use(
            http.post("/api/object_store_instances", ({ response }) => {
                return response(200).json(FAKE_OBJECT_STORE);
            }),
            http.post("/api/object_store_instances/test", ({ response }) => {
                return response(200).json(OK_PLUGIN_STATUS);
            }),
        );

        const wrapper = mountCreateForm(OPTIONAL_SECRET_TEMPLATE);

        const nameForElement = wrapper.find("#form-element-_meta_name");
        await nameForElement.find("input").setValue("My New Name");

        // Don't fill in the optional secret

        const submitElement = wrapper.find("#submit");
        expect(submitElement.classes()).not.toContain("g-disabled");

        await submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(1);
    });

    it("validates an optional variable when populated and enables submission after correction", async () => {
        const wrapper = mountCreateForm(OPTIONAL_VAR_WITH_VALIDATION_TEMPLATE);

        const nameForElement = wrapper.find("#form-element-_meta_name");
        await nameForElement.find("input").setValue("My New Name");

        // Set optional field to a value that's too short
        const optionalVarElement = wrapper.find("#form-element-optional_var");
        await optionalVarElement.find("input").setValue("abc"); // Too short (< 5 chars)
        await flushPromises();

        const submitElement = wrapper.find("#submit");
        expect(submitElement.classes()).toContain("g-disabled");

        // Fix the validation error
        await optionalVarElement.find("input").setValue("validvalue");
        await flushPromises();

        expect(submitElement.classes()).not.toContain("g-disabled");
    });
});
