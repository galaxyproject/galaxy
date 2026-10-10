import { getFakeObjectStoreInstance } from "@tests/test-data/objectStores";
import { createTestRouter, getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { afterEach, describe, expect, it } from "vitest";

import { useServerMock } from "@/api/client/__mocks__";
import { OK_PLUGIN_STATUS } from "@/components/ConfigTemplates/test_fixtures";
import type { ObjectStoreTemplateSummary } from "@/components/ObjectStore/Templates/types";

import UpgradeForm from "./UpgradeForm.vue";

const { server, http } = useServerMock();

enableAutoUnmount(afterEach);

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
            optional: true,
        },
        {
            name: "newvar",
            type: "string",
            help: "new var help",
            default: "",
            optional: true,
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
            optional: true, // New secret is optional
        },
    ],
    id: "moo",
    version: 2,
    badges: [],
    hidden: false,
};

const INSTANCE = getFakeObjectStoreInstance({
    name: "moo",
    template_id: "moo",
    template_version: 1,
    variables: {
        oldvar: "my old value",
        droppedvar: "this will be dropped",
    },
    secrets: ["oldsecret", "droppedsecret"],
    uuid: "112f889f-72d7-4619-a8e8-510a8c685aa7",
});

function mountUpgradeForm() {
    const router = createTestRouter();
    // Render real inputs and submission children; a fresh router isolates successful navigation.
    const wrapper = mount(UpgradeForm, {
        props: {
            latestTemplate: structuredClone(STANDARD_TEMPLATE),
            instance: structuredClone(INSTANCE),
        },
        global: withPlugins(getLocalVue(true), router),
    });
    return { wrapper, router };
}

describe("UpgradeForm", () => {
    it("prefills retained variables from the current instance", async () => {
        const { wrapper } = mountUpgradeForm();
        await flushPromises();

        const varFormEl = wrapper.find("#form-element-oldvar");
        expect(varFormEl.exists()).toBe(true);
        const inputField = varFormEl.get<HTMLInputElement>("input").element;
        expect(inputField.value).toBe("my old value");
    });

    it("leaves newly introduced variables empty", async () => {
        const { wrapper } = mountUpgradeForm();
        await flushPromises();

        const varFormEl = wrapper.find("#form-element-newvar");
        expect(varFormEl.exists()).toBe(true);
        const inputField = varFormEl.get<HTMLInputElement>("input").element;
        expect(inputField.value).toBe("");
    });

    it("returns to the index with a confirmation after a successful upgrade", async () => {
        server.use(
            http.post("/api/object_store_instances/{uuid}/test", ({ response }) => {
                return response(200).json(OK_PLUGIN_STATUS);
            }),
            http.put("/api/object_store_instances/{uuid}", ({ response }) => {
                return response(200).json(INSTANCE);
            }),
        );
        const { wrapper, router } = mountUpgradeForm();

        await flushPromises();
        const submitElement = wrapper.find("#submit");
        await submitElement.trigger("click");
        await flushPromises();
        const route = router.currentRoute.value;
        expect(route.path).toBe("/object_store_instances/index");
        expect(route.query.message).toBe("Upgraded storage location moo");
    });

    it("shows the upgrade error and emits no created instance when the update fails", async () => {
        server.use(
            http.post("/api/object_store_instances/{uuid}/test", ({ response }) => {
                return response(200).json(OK_PLUGIN_STATUS);
            }),
            http.put("/api/object_store_instances/{uuid}", ({ response }) => {
                return response("4XX").json({ err_msg: "problem upgrading", err_code: 400 }, { status: 400 });
            }),
        );
        const { wrapper } = mountUpgradeForm();
        await flushPromises();
        const submitElement = wrapper.find("#submit");
        expect(wrapper.find("[data-description='object-store-upgrade-error']").exists()).toBe(false);
        await submitElement.trigger("click");
        await flushPromises();
        const emitted = wrapper.emitted("created") || [];
        expect(emitted).toHaveLength(0);
        const errorEl = wrapper.find("[data-description='object-store-upgrade-error']");
        expect(errorEl.exists()).toBe(true);
        expect(errorEl.text()).toContain("problem upgrading");
    });
});
