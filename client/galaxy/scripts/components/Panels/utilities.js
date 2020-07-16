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
            //Sorts tools in section by rank in results
            toolRes.sort((tool1, tool2) => {
                return results.indexOf(tool1.id) - results.indexOf(tool2.id);
            });

            return {
                ...section,
                elems: toolRes,
            };
        });

        //Filter out categories without tools in results
        return filteredLayout
            .filter((section) => {
                const isSection = section.elems && section.elems.length > 0;
                const isMatchedTool = !section.text && results.includes(section.id);
                return isSection || isMatchedTool;
            })
            .sort((sect1, sect2) => {
                return results.indexOf(sect1.elems[0].id) - results.indexOf(sect2.elems[0].id);
            });
    } else {
        return layout;
    }
}

export function filterTools(layout, results) {
    // don't consider expression tools, unless it's workflow editor
    layout = layout.filter((section) => section.name !== "Expression Tools");

    if (results) {
        var toolsResults = [];
        if (results.length < 1) {
            return toolsResults;
        }

        //Goes through each section and adds each tools that's in results to
        //toolsResults, sorted by search ranking
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
