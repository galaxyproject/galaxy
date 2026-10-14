import { composeStories } from "@storybook/vue3-vite";
import { nth } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as RepositoryToolsStories from "./RepositoryTools.stories";

const stories = composeStories(RepositoryToolsStories);
const mountStory = useStoryMount();

describe("RepositoryTools", () => {
    it("shows the tool ID and version in repository details", () => {
        const [tool] = stories.SingleTool.args.tools;
        const wrapper = mountStory(stories.SingleTool);
        const cells = wrapper.findAll("td");
        const idCell = nth(cells, 0);
        expect(idCell.text()).toBe(tool.id);
        const versionCell = nth(cells, 1);
        expect(versionCell.text()).toBe(tool.version);
        expect(wrapper.findAll("tr").length).toBe(1);
        expect(wrapper.find("a").exists()).toBe(false);
    });

    it("expands and collapses the repository tool versions", async () => {
        const [firstTool, secondTool, thirdTool] = stories.SeveralTools.args.tools;
        const wrapper = mountStory(stories.SeveralTools);
        const rows = wrapper.findAll("tr");
        expect(rows.length).toBe(3);
        const firstRow = nth(rows, 0);
        expect(firstRow.get("td:first-child").text()).toBe(firstTool.id);
        expect(firstRow.get("td:last-child").text()).toBe(firstTool.version);
        const secondRow = nth(rows, 1);
        expect(secondRow.get("td:first-child").text()).toBe(secondTool.id);
        expect(secondRow.get("td:last-child").text()).toBe(secondTool.version);
        const expandRow = nth(rows, 2);
        expect(expandRow.get("td:first-child").text()).toBe("Show more");
        expect(expandRow.get("td:last-child").text()).toBe("");
        const expandLink = wrapper.get("a");
        await expandLink.trigger("click");

        const expandedRows = wrapper.findAll("tr");
        expect(expandedRows.length).toBe(4);
        const thirdToolRow = nth(expandedRows, 3);
        expect(thirdToolRow.get("td:first-child").text()).toBe(thirdTool.id);
        expect(thirdToolRow.get("td:last-child").text()).toBe(thirdTool.version);
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
