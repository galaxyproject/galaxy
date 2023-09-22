import { mount } from "@vue/test-utils";
import { getLocalVue } from "tests/jest/helpers";
import Monitor from "./Monitor";

jest.mock("app");

import { getAppRoot } from "onload/loadConfig";
jest.mock("onload/loadConfig");
getAppRoot.mockImplementation(() => "/");

import { Services } from "../services";
jest.mock("../services");

Services.mockImplementation(() => {
    return {
        async getInstalledRepositories() {
            return [
                {
                    name: "name_0",
                    owner: "owner_0",
                    status: "status_0_0",
                    description: "description_0_0",
                },
                {
                    name: "name_1",
                    owner: "owner_1",
                    status: "status_1",
                    description: "description_1",
                },
            ];
        },
    };
});

describe("Monitor", () => {
    it("test monitor", async () => {
        const localVue = getLocalVue();
        const wrapper = mount(Monitor, { localVue });
        await localVue.nextTick();
        const headers = wrapper.findAll("th");
        expect(headers.length).toBe(3);
        expect(headers.at(0).text()).toBe("Name");
        expect(headers.at(1).text()).toBe("Status");

        const cells = wrapper.findAll("td");
        expect(cells.length).toBe(6);
        expect(cells.at(0).text()).toBe("name_0 (owner_0)");
        expect(cells.at(1).text()).toContain("status_0_0");
        expect(cells.at(3).text()).toBe("name_1 (owner_1)");
        expect(cells.at(4).text()).toContain("status_1");
    });
});
