import { mount } from "@vue/test-utils";
import { getLocalVue } from "jest/helpers";
import Lint from "./Lint";
import { UntypedParameters } from "./modules/parameters";

jest.mock("app");

const localVue = getLocalVue();

describe("Lint", () => {
    let wrapper;

    beforeEach(() => {
        const untypedParameters = new UntypedParameters();
        wrapper = mount(Lint, {
            propsData: {
                untypedParameters: untypedParameters,
                nodes: {
                    "1": {
                        id: "1",
                        title: "",
                        label: "",
                        annotation: "",
                        inputTerminals: {},
                        outputTerminals: {},
                        activeOutputs: {
                            getAll() {
                                return [];
                            },
                        },
                    },
                    "2": {
                        id: "2",
                        title: "",
                        label: "",
                        annotation: "",
                        inputTerminals: {},
                        activeOutputs: {
                            getAll() {
                                return [];
                            },
                        },
                    },
                },
                annotation: "annotation",
                license: null,
                creator: null,
            },
            localVue,
        });
    });

    it("test checked vs unchecked issues", async () => {
        const checked = wrapper.findAll("[data-icon='check']");
        expect(checked.length).toBe(5);
        const unchecked = wrapper.findAll("[data-icon='exclamation-triangle']");
        expect(unchecked.length).toBe(2);
    });
});
