import { mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue, injectTestRouter } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";
import { type ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";

import { type UserConcreteObjectStore } from "./types";

import UpgradeForm from "./UpgradeForm.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue(true);
const router = injectTestRouter(localVue);

const STANDARD_TEMPLATE: ObjectStoreTemplateSummary = {
    type: "aws_s3",
    name: "moo",
    description: null,
    variables: [
        {
            name: "oldvar",
            type: "string",
            help: "old var help",
            default: "old default",
        },
        {
            name: "newvar",
            type: "string",
            help: "new var help",
            default: "",
        },
    ],
    secrets: [
        {
            name: "oldsecret",
            help: "old secret help",
        },
        {
            name: "newsecret",
            help: "new secret help",
        },
    ],
    id: "moo",
    version: 2,
    badges: [],
    hidden: false,
};

const INSTANCE: UserConcreteObjectStore = {
    type: "aws_s3",
    name: "moo",
    description: undefined,
    template_id: "moo",
    template_version: 1,
    badges: [],
    variables: {
        oldvar: "my old value",
        droppedvar: "this will be dropped",
    },
    secrets: ["oldsecret", "droppedsecret"],
    quota: { enabled: false },
    private: false,
    uuid: "112f889f-72d7-4619-a8e8-510a8c685aa7",
    active: true,
    hidden: false,
    purged: false,
};

describe("UpgradeForm", () => {
    it("should render with old variable values re-filled in", async () => {
        const wrapper = mount(UpgradeForm, {
            propsData: {
                latestTemplate: STANDARD_TEMPLATE,
                instance: INSTANCE,
            },
            localVue,
            router,
        });
        await flushPromises();

        const varFormEl = wrapper.find("#form-element-oldvar");
        expect(varFormEl).toBeTruthy();
        const inputField: HTMLInputElement = varFormEl.find("input").element as HTMLInputElement;
        expect(inputField.value).toBe("my old value");
    });

    it("should render with new variable values with empty values", async () => {
        const wrapper = mount(UpgradeForm, {
            propsData: {
                latestTemplate: STANDARD_TEMPLATE,
                instance: INSTANCE,
            },
            localVue,
            router,
        });
        await flushPromises();

        const varFormEl = wrapper.find("#form-element-newvar");
        expect(varFormEl).toBeTruthy();
        const inputField: HTMLInputElement = varFormEl.find("input").element as HTMLInputElement;
        expect(inputField.value).toBe("");
    });

    it("should put to update on submit and return to index", async () => {
        const wrapper = mount(UpgradeForm, {
            propsData: {
                latestTemplate: STANDARD_TEMPLATE,
                instance: INSTANCE,
            },
            localVue,
            router,
        });
        server.use(
            http.put("/api/object_store_instances/{user_object_store_id}", ({ response }) => {
                return response(200).json(INSTANCE);
            })
        );

        await flushPromises();
        const submitElement = wrapper.find("#submit");
        submitElement.trigger("click");
        await flushPromises();
        const route = wrapper.vm.$route;
        expect(route.path).toBe("/object_store_instances/index");
        expect(route.query.message).toBe("Upgraded storage location moo");
    });

    it("should indicate an error on failure", async () => {
        const wrapper = mount(UpgradeForm, {
            propsData: {
                latestTemplate: STANDARD_TEMPLATE,
                instance: INSTANCE,
            },
            localVue,
            router,
        });
        server.use(
            http.put("/api/object_store_instances/{user_object_store_id}", ({ response }) => {
                return response("4XX").json({ err_msg: "problem upgrading", err_code: 400 }, { status: 400 });
            })
        );

        await flushPromises();
        const submitElement = wrapper.find("#submit");
        expect(wrapper.find(".object-store-instance-upgrade-error").exists()).toBe(false);
        submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(0);
        const errorEl = wrapper.find(".object-store-instance-upgrade-error");
        expect(errorEl.exists()).toBe(true);
        expect(errorEl.html()).toContain("problem upgrading");
    });
});
