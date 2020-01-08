import _ from "underscore";

export function toolsLayout(layout, results) {
    if (results) {
        return _.filter(
            _.map(layout, category => {
                return {
                    ...category,
                    elems: (filtered => {
                        return _.filter(filtered, (el, i) => {
                            if (el.model_class.endsWith("ToolSectionLabel")) {
                                return filtered[i + 1] && filtered[i + 1].model_class.endsWith("Tool");
                            } else {
                                return true;
                            }
                        });
                    })(
                        _.filter(category.elems, el => {
                            if (el.model_class.endsWith("ToolSectionLabel")) {
                                return true;
                            } else {
                                return results.includes(el.id);
                            }
                        })
                    )
                };
            }),
            category => {
                return (
                    category.elems.length ||
                    (category.model_class.endsWith("Tool") && results.includes(category.id))
                );
            }
        );
    } else {
        return layout;
    }
}