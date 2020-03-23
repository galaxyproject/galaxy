export function filterToolSections(layout, results) {
    if (results) {
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
        return filteredLayout.filter((category) => {
            const isSection = category.elems && category.elems.length > 0;
            const isMatchedTool = !category.text && results.includes(category.id);
            return isSection || isMatchedTool;
        });
    } else {
        return layout;
    }
}
