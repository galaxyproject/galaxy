export function filterToolsinCats(layout, results) {
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
            toolRes.sort((el1, el2) => {
                if (results.indexOf(el1.id) < results.indexOf(el2.id)) {
                    return -1;
                } else {
                    return 1;
                }
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
                if (results.indexOf(sect1.elems[0].id) < results.indexOf(sect2.elems[0].id)) {
                    return -1;
                } else {
                    return 1;
                }
            });
    } else {
        return layout;
    }
}

export function filterTools(layout, results) {
    if (results) {
        var toolsResults = [results.length];

        //Goes through each section and adds each tools that's in results to
        //toolsResults, sorted by search ranking
        layout.map((section) => {
            if (section.elems) {
                section.elems.forEach((el) => {
                    if (!el.text && results.includes(el.id)) {
                        toolsResults[results.indexOf(el.id)] = el;
                    }
                });
            }
        });
        return toolsResults;
    } else {
        return layout;
    }
}
