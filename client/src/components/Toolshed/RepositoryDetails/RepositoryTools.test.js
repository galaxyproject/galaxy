import { getLocalVue, nth } from "@tests/vitest/helpers";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";

import RepositoryTools from "./RepositoryTools.vue";

const localVue = getLocalVue();

describe("RepositoryTools", () => {
    enableAutoUnmount(afterEach);

    it("shows the tool ID and version in repository details", () => {
        const wrapper = mount(RepositoryTools, {
            props: {
                tools: [
                    {
                        guid: "guid",
                        id: "id",
                        version: "version",
                    },
                ],
            },
            global: localVue,
        });
        const cells = wrapper.findAll("td");
        const idCell = nth(cells, 0);
        expect(idCell.text()).toBe("id");
        const versionCell = nth(cells, 1);
        expect(versionCell.text()).toBe("version");
    });

    it("expands and collapses the repository tool versions", async () => {
        const wrapper = mount(RepositoryTools, {
            props: {
                tools: [
                    {
                        guid: "guid_1",
                        id: "id_1",
                        version: "version_1",
                    },
                    {
                        guid: "guid_2",
                        id: "id_2",
                        version: "version_2",
                    },
                    {
                        guid: "guid_3",
                        id: "id_3",
                        version: "version_3",
                    },
                ],
            },
        });
        const rows = wrapper.findAll("tr");
        expect(rows.length).toBe(3);
        const firstRow = nth(rows, 0);
        expect(firstRow.get("td:first-child").text()).toBe("id_1");
        expect(firstRow.get("td:last-child").text()).toBe("version_1");
        const secondRow = nth(rows, 1);
        expect(secondRow.get("td:first-child").text()).toBe("id_2");
        expect(secondRow.get("td:last-child").text()).toBe("version_2");
        const expandRow = nth(rows, 2);
        expect(expandRow.get("td:first-child").text()).toBe("Show more");
        expect(expandRow.get("td:last-child").text()).toBe("");
        const expandLink = wrapper.get("a");
        await expandLink.trigger("click");

        const expandedRows = wrapper.findAll("tr");
        expect(expandedRows.length).toBe(4);
        const thirdToolRow = nth(expandedRows, 3);
        expect(thirdToolRow.get("td:first-child").text()).toBe("id_3");
        expect(thirdToolRow.get("td:last-child").text()).toBe("version_3");
        const collapseRow = nth(expandedRows, 0);
        expect(collapseRow.get("td:first-child").text()).toBe("Show less");
        expect(collapseRow.get("td:last-child").text()).toBe("");
        const collapseLink = wrapper.get("a");
        await collapseLink.trigger("click");

        const collapsedRows = wrapper.findAll("tr");
        expect(collapsedRows.length).toBe(3);
        const expandRowAfterCollapse = nth(collapsedRows, 2);
        expect(expandRowAfterCollapse.get("td:first-child").text()).toBe("Show more");
        expect(expandRowAfterCollapse.get("td:last-child").text()).toBe("");
    });
});
