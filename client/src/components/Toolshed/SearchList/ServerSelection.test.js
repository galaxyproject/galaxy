import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import ServerSelection from "./ServerSelection.vue";

enableAutoUnmount(afterEach);

function mountServerSelection() {
    return mount(ServerSelection, {
        props: {
            toolshedUrl: "url_0",
            toolshedUrls: ["url_0", "url_1"],
            loading: false,
            total: 10,
        },
        global: getLocalVue(),
    });
}

describe("ServerSelection", () => {
    it("shows the repository count, selected server, and available servers", () => {
        const wrapper = mountServerSelection();

        expect(wrapper.get(".description").text()).toBe("10 repositories available at");
        expect(wrapper.get("#dropdownToolshedUrl").text()).toBe("url_0");
        expect(wrapper.findAll(".dropdown-item").map((option) => option.text())).toEqual(["url_0", "url_1"]);
        expect(wrapper.find(".dropdown-menu").exists()).toBe(true);
    });

    it("emits the chosen server when another dropdown option is clicked", async () => {
        const wrapper = mountServerSelection();

        await wrapper.get(".dropdown-item:last-child").trigger("click");

        expect(emittedArg(wrapper, "onToolshed")).toBe("url_1");
        expect(wrapper.emitted("onToolshed")).toHaveLength(1);
    });
});
