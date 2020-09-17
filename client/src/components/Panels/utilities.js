export function filterToolSections(layout, results) {
    if (results) {
        const filteredLayout = layout.map((section) => {
            var toolRes = [];
            if (section.elems) {
                section.elems.forEach((el) => {
                    if (!el.text && results.includes(el.id)) {
                        toolRes.push(el);
                    }
                });
            }
            // sort tools in section by rank in results
            toolRes.sort((tool1, tool2) => {
                return results.indexOf(tool1.id) - results.indexOf(tool2.id);
            });

            return {
                ...section,
                elems: toolRes,
            };
        });
        // filter out categories without tools in results
        return filteredLayout
            .filter((section) => {
                const isSection = section.elems && section.elems.length > 0;
                const isMatchedTool = !section.text && results.includes(section.id);
                return isSection || isMatchedTool;
            })
            .sort((sect1, sect2) => {
                if (sect1.elems.length == 0 || sect2.elems.length == 0) {
                    return 0;
                }
                return results.indexOf(sect1.elems[0].id) - results.indexOf(sect2.elems[0].id);
            });
    } else {
        return layout;
    }
}

export function filterTools(layout, results) {
    // do not consider expression tools, unless requested by the workflow editor
    layout = layout.filter((section) => section.name !== "Expression Tools");
    if (results) {
        var toolsResults = [];
        if (results.length < 1) {
            return toolsResults;
        }
        // iterate through each section and add each tool that is in the results to
        // toolsResults, sort by search ranking
        layout.map((section) => {
            if (section.elems) {
                section.elems.forEach((el) => {
                    if (!el.text && results.includes(el.id)) {
                        toolsResults.push(el);
                    }
                });
            }
        });
        return toolsResults.sort((tool1, tool2) => {
            return results.indexOf(tool1.id) - results.indexOf(tool2.id);
        });
    } else {
        return layout;
    }
}
