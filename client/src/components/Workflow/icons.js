import { library } from "@fortawesome/fontawesome-svg-core";
import { faFile } from "@fortawesome/free-regular-svg-icons";
import { faFolderOpen, faPause, faPencilAlt, faSitemap, faWrench } from "@fortawesome/free-solid-svg-icons";

library.add(faWrench, faFile, faSitemap, faPencilAlt, faPause, faFolderOpen);

export default {
    tool: "fa-wrench",
    data_input: "fa-file-o fa-file", // fa-file-o for older FontAwesome, fa-file is the only thing I could find newer font awesome
    data_collection_input: "fa-folder-o fa-folder-open",
    subworkflow: "fa-sitemap fa-rotate-270",
    parameter_input: "fa-pencil-alt", // fa-pencil for older FontAwesome, fa-pencil-alt for newer
    pause: "fa-pause",
};
