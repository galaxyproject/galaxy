import FilesDialog from "./FilesDialog";
import SelectionDialogMixin from "components/SelectionDialog/SelectionDialogMixin";
import SelectionDialog from "components/SelectionDialog/SelectionDialog";
import DataDialogTable from "components/SelectionDialog/DataDialogTable";
import { shallowMount, mount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "jest/helpers";
import MockAdapter from "axios-mock-adapter";
import axios from "axios";
import { rootResponse } from "./testingData";

jest.mock("app");

// const mockOptions = {
//     callback: () => {},
//     history: "history",
//     modalStatic: true,
// };
const transitionStub = () => ({
    render: function (h) {
        return this.$options._renderChildren;
    },
});
describe("FilesDialog/FilesDialog.vue", () => {
    const localVue = getLocalVue();

    let wrapper;
    let axiosMock;
    const propsData = {
        multiple: true,
    };

    beforeEach(async () => {
        axiosMock = new MockAdapter(axios);

        wrapper = mount(FilesDialog, {
            propsData: {
                multiple: true,
            },
        });

        axiosMock.onGet("/api/remote_files/plugins").reply(200, rootResponse);
        console.log("i'm here");

        await flushPromises();
    });

    it("should not render a div if no plugins found in store", async () => {
        console.log("!!!!");
        console.log(wrapper.find("table").exists());
        console.log(wrapper.vm.items);
        console.log("length", wrapper.html().length);
        console.log("text", wrapper.text());
        console.log("!!!!");
    });
});
