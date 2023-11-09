import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";

import Filtering from "@/utils/filtering";

import MountTarget from "./GridList.vue";

const localVue = getLocalVue();

const testGrid = {
    actions: [
        {
            title: "test",
            icon: "plus",
            handler: () => {},
        },
    ],
    fields: [
        {
            key: "id",
            title: "id",
            type: "text",
        },
        {
            key: "link",
            title: "link",
            type: "link",
        },
    ],
    filtering: new Filtering({}, undefined, false, false),
    getData: () => {
        const data = [
            {
                id: "id-1",
                link: "link-1",
            },
            {
                id: "id-2",
                link: "link-2",
            },
        ];
        return [data, data.length];
    },
    plural: "Tests",
    sortBy: "update_time",
    sortDesc: true,
    sortKeys: ["create_time", "title", "update_time"],
    title: "Test",
};

function createTarget(propsData) {
    return mount(MountTarget, {
        localVue,
        propsData,
        stubs: {
            Icon: true,
        },
    });
}

describe("GridList", () => {
    it("basic rendering", async () => {
        const wrapper = createTarget({
            config: testGrid,
        });
        const findInput = wrapper.find("[data-description='filter text input']");
        expect(findInput.attributes().placeholder).toBe("search tests");
        expect(wrapper.find(".loading-message").text()).toBe("Loading...");
        const findAction = wrapper.find("[data-description='grid action test']");
        expect(findAction.text()).toBe("test");
        await wrapper.vm.$nextTick();
        expect(wrapper.find("[data-description='grid cell 0-0']").text()).toBe("id-1");
        expect(wrapper.find("[data-description='grid cell 1-0']").text()).toBe("id-2");
        expect(wrapper.find("[data-description='grid cell 0-1'] > a").text()).toBe("link-1");
        expect(wrapper.find("[data-description='grid cell 1-1'] > a").text()).toBe("link-2");
    });
});
