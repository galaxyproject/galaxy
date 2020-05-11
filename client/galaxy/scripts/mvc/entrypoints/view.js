import $ from "jquery";
import GridView from "mvc/grid/grid-view";
import { clearPolling, pollUntilActive } from "mvc/entrypoints/poll";

export default GridView.extend({
    init_grid_elements: function () {
        GridView.prototype.init_grid_elements.call(this);

        const activated = {};

        const onUpdate = (entryPoints) => {
            entryPoints.forEach((entryPoint) => {
                const entryPointId = entryPoint.id;
                if (entryPoint.active && !activated[entryPointId]) {
                    const $link = $(`.entry-point-link[entry_point_id='${entryPointId}']`);
                    if ($link.length > 0) {
                        $link.attr("href", entryPoint["target"]);
                        activated[entryPointId] = true;
                    }
                }
            });
        };
        const onError = (e) => {
            console.error(e);
        };
        pollUntilActive(onUpdate, onError, { running: true });
    },
    remove: function () {
        // Your processing code here
        clearPolling();
        GridView.prototype.remove.apply(this, arguments);
    },
});
