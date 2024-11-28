import { createLocalVue, shallowMount } from "@vue/test-utils";

import { Model } from "./model";
import { Services } from "./services";
import { UrlTracker } from "./utilities";

import DataDialog from "./DataDialog.vue";
import SelectionDialog from "components/SelectionDialog/SelectionDialog.vue";

jest.mock("app");

const mockOptions = {
    callback: () => {},
    history: "history",
    modalStatic: true,
};

describe("model.js", () => {
    let result = null;
    it("Model operations for single, no format", () => {
        const model = new Model();
        try {
            model.add({ idx: 1 });
            throw Error("Accepted invalid record.");
        } catch (error) {
            expect(error.message).toBe("Invalid record with no <id>.");
        }
        model.add({ id: 1 });
        expect(model.count()).toBe(1);
        expect(model.exists(1)).toBe(true);
        model.add({ id: 2, tag: "tag" });
        expect(model.count()).toBe(1);
        expect(model.exists(1)).toBe(false);
        expect(model.exists(2)).toBe(true);
        result = model.finalize();
        expect(result.id).toBe(2);
        expect(result.tag).toBe("tag");
    });

    it("Model operations for multiple, with format", () => {
        const model = new Model({ multiple: true, format: "tag" });
        model.add({ id: 1, tag: "tag_1" });
        expect(model.count()).toBe(1);
        model.add({ id: 2, tag: "tag_2" });
        expect(model.count()).toBe(2);
        result = model.finalize();
        expect(result.length).toBe(2);
        expect(result[0]).toBe("tag_1");
        expect(result[1]).toBe("tag_2");
        model.add({ id: 1 });
        expect(model.count()).toBe(1);
        result = model.finalize();
        expect(result[0]).toBe("tag_2");
    });
});

describe("utilities.js/UrlTracker", () => {
    it("Test url tracker", () => {
        const urlTracker = new UrlTracker("url_initial");
        let url = urlTracker.getUrl();
        expect(url).toBe("url_initial");
        expect(urlTracker.atRoot()).toBe(true);
        url = urlTracker.getUrl("url_1");
        expect(url).toBe("url_1");
        expect(urlTracker.atRoot()).toBe(false);
        url = urlTracker.getUrl("url_2");
        expect(url).toBe("url_2");
        expect(urlTracker.atRoot()).toBe(false);
        url = urlTracker.getUrl();
        expect(url).toBe("url_1");
        expect(urlTracker.atRoot()).toBe(false);
        url = urlTracker.getUrl();
        expect(url).toBe("url_initial");
        expect(urlTracker.atRoot()).toBe(true);
    });
});

describe("services/Services:isDataset", () => {
    it("Test dataset identifier", () => {
        const services = new Services(mockOptions);
        expect(services.isDataset({})).toBe(false);
        expect(services.isDataset({ history_content_type: "dataset" })).toBe(true);
        expect(services.isDataset({ history_content_type: "xyz" })).toBe(false);
        expect(services.isDataset({ type: "file" })).toBe(true);
        expect(services.getRecord({ hid: 1, history_content_type: "dataset" }).isLeaf).toBe(true);
        expect(services.getRecord({ hid: 2, history_content_type: "xyz" }).isLeaf).toBe(false);
        expect(services.getRecord({ type: "file" }).isLeaf).toBe(true);
    });
});

describe("services.js/Services", () => {
    it("Test data population from raw data", () => {
        const rawData = {
            hid: 1,
            id: 1,
            history_id: 0,
            name: "name_1",
        };
        const services = new Services(mockOptions);
        const items = services.getItems(rawData);
        expect(items.length).toBe(1);
        const first = items[0];
        expect(first.label).toBe("1: name_1");
        expect(first.download).toBe("http://localhost:/api/histories/0/contents/1/display");
    });
});

describe("DataDialog.vue", () => {
    let wrapper;
    /*
    const rawData = [
        {
            id: 1,
            hid: 1,
            name: "dataset_1",
            history_content_type: "dataset",
        },
        {
            id: 2,
            name: "dataset_2",
            type: "file",
        },
        {
            id: 3,
            hid: 3,
            name: "collection_1",
            history_content_type: "dataset_collection",
        },
    ];
    */

    it("loads correctly, embeds a SelectionDialog", () => {
        const localVue = createLocalVue();
        wrapper = shallowMount(DataDialog, {
            propsData: mockOptions,
            localVue,
            stubs: {
                Icon: true,
            },
        });
        expect(wrapper.findComponent(SelectionDialog).exists()).toBe(true);
        // Cannot get nested slot templates to render into the wrapper
        ///  Lots of open issues around this
        ///  ... Maybe because named slots have many issues
        //   - https://github.com/vuejs/vue-test-utils/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aopen+slot
        //   ... Maybe because it is a modal and no longer inside the template DOM element?
        //   - https://github.com/vuejs/vue-test-utils/issues/1333

        // expect(wrapper.find(".fa-spinner").text()).to.equals("");
        // expect(wrapper.contains(".fa-spinner")).to.equals(true);
        // await wrapper.vm.$nextTick();
        // expect(wrapper.findAll(".fa-folder").length).to.equals(2);
        // expect(wrapper.findAll(".fa-file-o").length).to.equals(2);

        // SelectionDialog DOM properties are tested now in SelectionDialog.test.js however.
    });
});
