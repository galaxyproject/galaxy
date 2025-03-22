import { init } from "astrovisjs/dist/astrovis/astrovis";

const incoming = document.getElementById("app").getAttribute("data-incoming") || "{}";
const { root, visualization_config } = JSON.parse(incoming);
const dataset_id = visualization_config.dataset_id;
const file_url = root + "datasets/" + dataset_id + "/display"

init('app', file_url);
