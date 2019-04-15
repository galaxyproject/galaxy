import sinon from "sinon";
import { mount } from "@vue/test-utils";
import DataDialog from "./DataDialog.vue";
import { __RewireAPI__ as rewire } from "./DataDialog";
import { Model } from "./model.js";
import { UrlTracker } from "./utilities.js";
import { Services } from "./services";
import Vue from "vue";

const mockOptions = {
    callback: () => {},
    host: "host",
    root: "root",
    history: "history"
};

describe("model.js", () => {
    let result = null;
    it("Model operations for single, no format", () => {
        let model = new Model();
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
        let model = new Model({ multiple: true, format: "tag" });
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
        let urlTracker = new UrlTracker("url_initial");
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
        let services = new Services(mockOptions);
        expect(services.isDataset({})).to.equals(false);
        expect(services.isDataset({ history_content_type: "dataset" })).to.equals(true);
        expect(services.isDataset({ history_content_type: "xyz" })).to.equals(false);
        expect(services.isDataset({ type: "file" })).to.equals(true);
        expect(services.getRecord({ hid: 1, history_content_type: "dataset" }).isDataset).to.equals(true);
        expect(services.getRecord({ hid: 2, history_content_type: "xyz" }).isDataset).to.equals(false);
        expect(services.getRecord({ type: "file" }).isDataset).to.equals(true);
    });
});

describe("services.js/Services", () => {
    it("Test data population from raw data", () => {
        let rawData = {
            hid: 1,
            id: 1,
            history_id: 0,
            name: "name_1"
        };
        let services = new Services(mockOptions);
        let items = services.getItems(rawData);
        expect(items.length).to.equals(1);
        let first = items[0];
        expect(first.name).to.equals("1: name_1");
        expect(first.download).to.equals("host/api/histories/0/contents/1/display");
    });
});

describe("DataDialog.vue", () => {
    let stub;
    let wrapper;
    let emitted;

    let rawData = [
        {
            id: 1,
            hid: 1,
            name: "dataset_1",
            history_content_type: "dataset"
        },
        {
            id: 2,
            name: "dataset_2",
            type: "file"
        },
        {
            id: 3,
            hid: 3,
            name: "collection_1",
            history_content_type: "dataset_collection"
        }
    ];

    let mockServices = class {
        get(url) {
            let services = new Services(mockOptions);
            let items = services.getItems(rawData);
            return new Promise((resolve, reject) => {
                resolve(items);
            });
        }
    };

    beforeEach(() => {
        rewire.__Rewire__("Services", mockServices);
    });

    afterEach(() => {
        if (stub) stub.restore();
    });

    it("loads correctly, shows alert", () => {
        wrapper = mount(DataDialog, {
            propsData: mockOptions
        });
        emitted = wrapper.emitted();
        expect(wrapper.classes()).contain("data-dialog-modal");
        expect(wrapper.find(".fa-spinner").text()).to.equals("");
        expect(wrapper.find(".btn-secondary").text()).to.equals("Clear");
        expect(wrapper.find(".btn-primary").text()).to.equals("Ok");
        expect(wrapper.contains(".fa-spinner")).to.equals(true);
        return Vue.nextTick().then(() => {
            expect(wrapper.findAll(".fa-copy").length).to.equals(2);
            expect(wrapper.findAll(".fa-file-o").length).to.equals(2);
        });
    });

    it("loads correctly, shows datasets and folders", () => {
        wrapper = mount(DataDialog, {
            propsData: mockOptions
        });
        emitted = wrapper.emitted();
        expect(wrapper.classes()).contain("data-dialog-modal");
        expect(wrapper.find(".fa-spinner").text()).to.equals("");
        expect(wrapper.find(".btn-secondary").text()).to.equals("Clear");
        expect(wrapper.find(".btn-primary").text()).to.equals("Ok");
        expect(wrapper.contains(".fa-spinner")).to.equals(true);
        return Vue.nextTick().then(() => {
            expect(wrapper.findAll(".fa-copy").length).to.equals(2);
            expect(wrapper.findAll(".fa-file-o").length).to.equals(2);
        });
    });
});
