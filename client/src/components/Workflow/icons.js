import { library } from "@fortawesome/fontawesome-svg-core";
import { faWrench, faSitemap, faPencilAlt, faPause } from "@fortawesome/free-solid-svg-icons";
import { faFolder, faFile } from "@fortawesome/free-regular-svg-icons";

library.add(faWrench, faSitemap, faPencilAlt, faPause);
library.add(faFolder, faFile);

export default {
    tool: "fa-wrench",
    data_input: "far fa-file",
    data_collection_input: "far fa-folder",
    subworkflow: "fa-sitemap fa-rotate-270",
    parameter_input: "fa-pencil-alt",
    pause: "fa-pause",
};
