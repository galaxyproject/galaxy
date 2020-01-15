import _ from "underscore";

export function filterToolSections(layout, results) {
    if (results) {
        return _.filter(
            _.map(layout, category => {
                return {
                    ...category,
                    elems: (filtered => {
                        return _.filter(filtered, (el, i) => {
                            if (el.text) {
                                return filtered[i + 1] && !filtered[i + 1].text;
                            } else {
                                return true;
                            }
                        });
                    })(
                        _.filter(category.elems, el => {
                            if (el.text) {
                                return true;
                            } else {
                                return results.includes(el.id);
                            }
                        })
                    )
                };
            }),
            category => {
                return category.elems.length || (!category.text && results.includes(category.id));
            }
        );
    } else {
        return layout;
    }
}
