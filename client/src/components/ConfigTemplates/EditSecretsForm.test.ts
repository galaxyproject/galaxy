import { getLocalVue } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import { STANDARD_FILE_SOURCE_TEMPLATE, STANDARD_OBJECT_STORE_TEMPLATE } from "./test_fixtures";

import EditSecretsForm from "./EditSecretsForm.vue";

const localVue = getLocalVue(true);

describe("EditSecretsForm", () => {
    it("should render a secrets for for file source templates", async () => {
        const wrapper = mount(EditSecretsForm as object, {
            props: {
                template: STANDARD_FILE_SOURCE_TEMPLATE,
                title: "Secrets FORM for file source",
            },
            global: localVue,
        });
        const titleText = wrapper.find(".portlet-title-text");
        expect(titleText.exists()).toBeTruthy();
        expect(titleText.text()).toEqual("Secrets FORM for file source");
    });

    it("should render a secrets for for object store templates", async () => {
        const wrapper = mount(EditSecretsForm as object, {
            props: {
                template: STANDARD_OBJECT_STORE_TEMPLATE,
                title: "Secrets FORM for object store",
            },
            global: localVue,
        });
        const titleText = wrapper.find(".portlet-title-text");
        expect(titleText.exists()).toBeTruthy();
        expect(titleText.text()).toEqual("Secrets FORM for object store");
    });
});
