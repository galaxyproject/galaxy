import { orderBy } from "lodash";

export class toolSearch {
    constructor() {
        this.toolsResults = [];
        this.toolsResultsSortLabel = "apiSort";
        this.toolsResultsSectionHide = "Expression Tools";
    }

    filter(tools, results) {
        if (this.hasResults(results)) {
            tools = this.normalizeTools(tools);
            this.toolsResults = this.mapToolsResults(tools, results);
            this.toolsResults = this.sortToolsResults(this.toolsResults);
        } else {
            this.toolsResults = tools;
        }

        return this.toolsResults;
    }

    filterSections(tools, results) {
        let toolsResultsSection = [];

        if (this.hasResults(results)) {
            this.toolsResults = tools.map((section) => {
                tools = this.flattenToolsSection(section);
                toolsResultsSection = this.mapToolsResults(tools, results);
                toolsResultsSection = this.sortToolsResults(toolsResultsSection);

                return {
                    ...section,
                    elems: toolsResultsSection,
                };
            });
            this.toolsResults = this.deleteEmptySections(this.toolsResults, results);
        } else {
            this.toolsResults = tools;
        }

        return this.toolsResults;
    }

    normalizeTools(tools) {
        tools = this.hideToolsSection(tools);
        tools = this.flattenTools(tools);

        return tools;
    }

    flattenToolsSection(section) {
        const flattenTools = [];

        if (section.elems) {
            section.elems.forEach((elem) => {
                if (!elem.text) {
                    flattenTools.push(elem);
                }
            });
        } else if (!section.text) {
            flattenTools.push(section);
        }

        return flattenTools;
    }

    mapToolsResults(tools, results) {
        this.toolsResults = tools
            .filter((tool) => !tool.text && results.includes(tool.id))
            .map((tool) => {
                Object.assign(tool, this.setSort(tool, results));
                return tool;
            });

        return this.toolsResults;
    }

    setSort(tool, results) {
        return { [this.toolsResultsSortLabel]: results.indexOf(tool.id) };
    }

    sortToolsResults(toolsResults) {
        return orderBy(toolsResults, [this.toolsResultsSortLabel], ["asc"]);
    }

    deleteEmptySections(tools, results) {
        let isSection = false;
        let isMatchedTool = false;

        tools = tools
            .filter((section) => {
                isSection = section.elems && section.elems.length > 0;
                isMatchedTool = !section.text && results.includes(section.id);
                return isSection || isMatchedTool;
            })
            .sort((sect1, sect2) => {
                if (sect1.elems.length == 0 || sect2.elems.length == 0) {
                    return 0;
                }
                return results.indexOf(sect1.elems[0].id) - results.indexOf(sect2.elems[0].id);
            });

        return tools;
    }

    hideToolsSection(tools) {
        return tools.filter((section) => section.name !== this.toolsPanelSectionHide);
    }

    flattenTools(tools) {
        let normalizedTools = [];

        tools.forEach((section) => {
            normalizedTools = normalizedTools.concat(this.flattenToolsSection(section));
        });

        return normalizedTools;
    }

    hasResults(results) {
        return Array.isArray(results) && results.length > 0;
    }
}
