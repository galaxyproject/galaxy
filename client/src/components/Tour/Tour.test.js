import { shallowMount } from "@vue/test-utils";
import flushPromises from "flush-promises";
import { getLocalVue } from "tests/jest/helpers";

import { useServerMock } from "@/api/client/__mocks__";

import TourList from "./TourList.vue";

const { server, http } = useServerMock();

const localVue = getLocalVue();

jest.mock("app");

const mockTours = [
    {
        id: "intro-to-galaxy",
        name: "Intro to Galaxy",
        description: "Learn the basics",
        tags: ["beginner"],
    },
    {
        id: "advanced-analysis",
        name: "Advanced Analysis",
        description: "Deep dive into tools",
        tags: ["advanced"],
    },
];

describe("Tour", () => {
    let wrapper;

    beforeEach(async () => {
        server.use(http.get("/api/tours", ({ response }) => response(200).json(mockTours)));
        wrapper = shallowMount(TourList, {
            propsData: {},
            localVue,
        });
        await flushPromises();
    });

    it("test tours", async () => {
        expect(wrapper.findAll("[data-description='tour link']").length).toBe(2);
    });
});
