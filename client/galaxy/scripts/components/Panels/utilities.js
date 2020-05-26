import { getGalaxyInstance } from "app";
import axios from "axios";

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
        return toolsResults;
    } else {
        return layout;
    }
}

export function resizePanel(newWidth) {
    document.getElementById("left").style["width"] = newWidth + "px";
    document.getElementById("center").style["left"] = newWidth + "px";
}

/*export function onFavorite(toolId) {
    //Add tool to user's favorites
    const Galaxy = getGalaxyInstance();
    axios.put(`${Galaxy.root}api/users/${Galaxy.user.id}/favorites/tools`, { object_id: toolId }).then((response) => {
        this.inFavorites = !this.inFavorites;
        Galaxy.user.updateFavorites("tools", response.data);
        ariaAlert("added to favorites");
    });
}

export function onUnfavorite(toolId) {
    //Remove tool from user's favorites
    const Galaxy = getGalaxyInstance();
    console.log("TOOL ID UNFAV:", toolId);
    axios
        .delete(`${Galaxy.root}api/users/${Galaxy.user.id}/favorites/tools/${encodeURIComponent(toolId)}`)
        .then((response) => {
            this.inFavorites = !this.inFavorites;
            Galaxy.user.updateFavorites("tools", response.data);
            ariaAlert("removed from favorites");
        });
}*/

export function getToolInputs(toolId) {
    const Galaxy = getGalaxyInstance();
    axios.get(`${Galaxy.root}api/tools/${toolId}/?io_details=true`).then((response) => {
        const firstInput = response.data.inputs[0];
        //this.inputTypes = firstInput.extensions ? firstInput.extensions : [];
    });
}
