export function filterToolSections(layout, results) {
    if (results) {
        //Goes through each category and filters out tools that were not in results
        const filteredLayout = layout.map((category) => {
            return {
                ...category,
                elems:
                    category.elems &&
                    category.elems.filter((el) => {
                        return !el.text && results.includes(el.id);
                    }),
            };
        });
        //Filters out to only display categories that have tools that were in results
        return filteredLayout.filter((category) => {
            const isSection = category.elems && category.elems.length > 0;
            const isMatchedTool = !category.text && results.includes(category.id);
            return isSection || isMatchedTool;
        });
    } else {
        return layout;
    }
}

export function filterTools(layout, results) {
    if (results) {
        var toolsResults = [results.length];

        layout.map((category) => {
            category.elems.forEach((el) => {
                if (!el.text && results.includes(el.id)) {
                    toolsResults[results.indexOf(el.id)] = el;
                }
            });
        });
        return toolsResults;
    } else {
        return layout;
    }
}
