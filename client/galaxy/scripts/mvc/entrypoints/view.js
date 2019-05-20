import $ from "jquery";
import axios from "axios";
import GridView from "mvc/grid/grid-view";
import { getAppRoot } from "onload";
import { Toast } from "ui/toast";

export default GridView.extend({
    init_grid_elements: function() {
        GridView.prototype.init_grid_elements.call(this);
        $(".entry-point-link").click(event => {
            const $link = $(event.target);
            const entry_point_id = $link.attr("entry_point_id");
            const url = `${getAppRoot()}api/entry_points/${entry_point_id}/access`;
            const handlerError = err => {
                let message = "Problem finding entry point target, please contact an admin.";
                if (err.response) {
                    message = err.response.data.err_msg;
                }
                Toast.error(message);
            };
            axios
                .get(url)
                .then(response => (window.location = response.data.target))
                .catch(handlerError);
        });
    }
});
