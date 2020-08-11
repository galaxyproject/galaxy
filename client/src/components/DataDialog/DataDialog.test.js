import DataDialog from "./DataDialog.vue";
import SelectionDialog from "components/SelectionDialog/SelectionDialog.vue";
import { __RewireAPI__ as rewire } from "./DataDialog";
import { Model } from "./model";
import { UrlTracker } from "./utilities";
import { Services } from "./services";
import { mount, createLocalVue } from "@vue/test-utils";

const mockOptions = {
    callback: () => {},
    host: "host",
    root: "root",
    history: "history",
    modalStatic: true,
};

describe("model.js", () => {
    let result = null;
    it("Model operations for single, no format", () => {
        const model = new Model();
        try {
            model.add({ idx: 1 });
            throw "Accepted invalid record.";
        } catch (error) {
            expect(error).to.equals("Invalid record with no <id>.");
        }
        model.add({ id: 1 });
        expect(model.count()).to.equals(1);
        expect(model.exists(1)).to.equals(true);
        model.add({ id: 2, tag: "tag" });
        expect(model.count()).to.equals(1);
        expect(model.exists(1)).to.equals(false);
        expect(model.exists(2)).to.equals(true);
        result = model.finalize();
        expect(result.id).to.equals(2);
        expect(result.tag).to.equals("tag");
    });
    it("Model operations for multiple, with format", () => {
        const model = new Model({ multiple: true, format: "tag" });
        model.add({ id: 1, tag: "tag_1" });
        expect(model.count()).to.equals(1);
        model.add({ id: 2, tag: "tag_2" });
        expect(model.count()).to.equals(2);
        result = model.finalize();
        expect(result.length).to.equals(2);
        expect(result[0]).to.equals("tag_1");
        expect(result[1]).to.equals("tag_2");
        model.add({ id: 1 });
        expect(model.count()).to.equals(1);
        result = model.finalize();
        expect(result[0]).to.equals("tag_2");
    });
});

describe("utilities.js/UrlTracker", () => {
    it("Test url tracker", () => {
        const urlTracker = new UrlTracker("url_initial");
        let url = urlTracker.getUrl();
        expect(url).to.equals("url_initial");
        expect(urlTracker.atRoot()).to.equals(true);
        url = urlTracker.getUrl("url_1");
        expect(url).to.equals("url_1");
        expect(urlTracker.atRoot()).to.equals(false);
        url = urlTracker.getUrl("url_2");
        expect(url).to.equals("url_2");
        expect(urlTracker.atRoot()).to.equals(false);
        url = urlTracker.getUrl();
        expect(url).to.equals("url_1");
        expect(urlTracker.atRoot()).to.equals(false);
        url = urlTracker.getUrl();
        expect(url).to.equals("url_initial");
        expect(urlTracker.atRoot()).to.equals(true);
    });
});

describe("services/Services:isDataset", () => {
    it("Test dataset identifier", () => {
        const services = new Services(mockOptions);
        expect(services.isDataset({})).to.equals(false);
        expect(services.isDataset({ history_content_type: "dataset" })).to.equals(true);
        expect(services.isDataset({ history_content_type: "xyz" })).to.equals(false);
        expect(services.isDataset({ type: "file" })).to.equals(true);
        expect(services.getRecord({ hid: 1, history_content_type: "dataset" }).isLeaf).to.equals(true);
        expect(services.getRecord({ hid: 2, history_content_type: "xyz" }).isLeaf).to.equals(false);
        expect(services.getRecord({ type: "file" }).isLeaf).to.equals(true);
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
        expect(items.length).to.equals(1);
        const first = items[0];
        expect(first.label).to.equals("1: name_1");
        expect(first.download).to.equals("host/api/histories/0/contents/1/display");
    });
});

describe("DataDialog.vue", () => {
    let wrapper;

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

    const mockServices = class {
        get(url) {
            const services = new Services(mockOptions);
            const items = services.getItems(rawData);
            return new Promise((resolve, reject) => {
                resolve(items);
            });
        }
    };

    beforeEach(() => {
        rewire.__Rewire__("getGalaxyInstance", () => {
            root: "root";
        });
        const localVue = createLocalVue();
        wrapper = mount(DataDialog, {
            propsData: mockOptions,
            attachToDocument: true,
            localVue,
        });
    });

    it("loads correctly, embeds a SelectionDialog", async () => {
        expect(wrapper.find(SelectionDialog).is(SelectionDialog)).to.equals(true);
        // Cannot get nested slot templates to render into the wrapper
        ///  Lots of open issues around this
        ///  ... Maybe because named slots have many issues
        //   - https://github.com/vuejs/vue-test-utils/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aopen+slot
        //   ... Maybe because it is a modal and no longer inside the template DOM element?
        //   - https://github.com/vuejs/vue-test-utils/issues/1333

        // expect(wrapper.find(".fa-spinner").text()).to.equals("");
        // expect(wrapper.contains(".fa-spinner")).to.equals(true);
        // await Vue.nextTick();
        // expect(wrapper.findAll(".fa-folder").length).to.equals(2);
        // expect(wrapper.findAll(".fa-file-o").length).to.equals(2);

        // SelectionDialog DOM properties are tested now in SelectionDialog.test.js however.
    });
});
