export function filterToolsinCats(layout, results) {
    if (results) {
        const filteredLayout = layout.map(category => {
            var toolRes = [];
            category.elems.forEach(el => {
                if (!el.text && results.includes(el.id)) {
                    toolRes.push(el);
                }
            });
            //Sorts tools in category by rank in results
            toolRes.sort((el1, el2) => {
                if (results.indexOf(el1.id) < results.indexOf(el2.id)) {
                  return -1;
                } else {
                  return 1;
                }
            });
            
            return {
                ...category,
                elems: toolRes
            };
        });

        //Filters out to only display categories that have tools that were in results
        return filteredLayout.filter(category => {
            const isSection = category.elems && category.elems.length > 0;
            const isMatchedTool = !category.text && results.includes(category.id);
            return isSection || isMatchedTool;
        }).sort((cat1, cat2) => {
            if (results.indexOf(cat1.elems[0].id) < results.indexOf(cat2.elems[0].id)) {
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

        //Goes through each category and adds each tools that's in results to 
        //toolsResults, sorted by search ranking
        layout.map(category => {
            category.elems.forEach(el => {
                if (!el.text && results.includes(el.id)) {
                    toolsResults[results.indexOf(el.id)] = el;
                }
            })
        });
        return toolsResults;
    } else {
        return layout;
    }
}