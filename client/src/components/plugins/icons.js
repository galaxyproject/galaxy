import { library } from "@fortawesome/fontawesome-svg-core";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import {
    faArrowUp,
    faBolt,
    faBurn,
    faChartArea,
    faCheckSquare,
    faClock,
    faCloud,
    faCodeBranch,
    faColumns,
    faCompress,
    faCopy,
    faDownload,
    faEllipsisH,
    faEllipsisV,
    faExchangeAlt,
    faEye,
    faFileArchive,
    faFileExport,
    faFilter,
    faFolder,
    faInfoCircle,
    faList,
    faLink,
    faLock,
    faPause,
    faPen,
    faPlay,
    faPlus,
    faQuestion,
    faShareAlt,
    faStream,
    faTags,
    faTrash,
    faTrashRestore,
    faExclamationTriangle,
    faUndo,
    faUserLock,
    faWrench,
} from "@fortawesome/free-solid-svg-icons";

library.add(
    faArrowUp,
    faBolt,
    faBurn,
    faChartArea,
    faCheckSquare,
    faClock,
    faCloud,
    faCodeBranch,
    faColumns,
    faCompress,
    faCopy,
    faDownload,
    faEllipsisH,
    faEllipsisV,
    faExchangeAlt,
    faEye,
    faFileArchive,
    faFileExport,
    faFilter,
    faFolder,
    faInfoCircle,
    faLink,
    faList,
    faLock,
    faPause,
    faPen,
    faPlay,
    faPlus,
    faQuestion,
    faShareAlt,
    faStream,
    faTags,
    faTrash,
    faTrashRestore,
    faExclamationTriangle,
    faUndo,
    faUserLock,
    faWrench
);

const glFilterSolid = {
    prefix: "gls",
    iconName: "filter",
    icon: [
        128,
        128,
        [],
        "e001",
        "M83,63.939L83,120.726C83,123.523 81.335,126.051 78.766,127.156C76.197,128.261 73.216,127.731 71.186,125.808C62.615,117.688 51.757,107.402 47.186,103.071C45.79,101.749 45,99.911 45,97.989C45,89.157 45,63.939 45,63.939C45,63.939 16.757,29.867 1.505,11.467C-0.226,9.379 -0.594,6.478 0.559,4.023C1.713,1.567 4.182,0 6.895,-0C34.536,-0 93.464,-0 121.105,-0C123.818,0 126.287,1.567 127.441,4.023C128.594,6.478 128.226,9.379 126.495,11.467C111.243,29.867 83,63.939 83,63.939Z",
    ],
};

const glFilterRegular = {
    prefix: "glr",
    iconName: "filter",
    icon: [
        128,
        128,
        [],
        "e002",
        "M83,63.939L83,120.726C83,123.523 81.335,126.051 78.766,127.156C76.197,128.261 73.216,127.731 71.186,125.808C62.615,117.688 51.757,107.402 47.186,103.071C45.79,101.749 45,99.911 45,97.989C45,89.157 45,63.939 45,63.939C45,63.939 16.757,29.867 1.505,11.467C-0.226,9.379 -0.594,6.478 0.559,4.023C1.713,1.567 4.182,0 6.895,-0C34.536,-0 93.464,-0 121.105,-0C123.818,0 126.287,1.567 127.441,4.023C128.594,6.478 128.226,9.379 126.495,11.467C111.243,29.867 83,63.939 83,63.939ZM56,59.972L56,96.269L72,111.426L72,59.972L112.594,11L15.406,11L56,59.972Z",
    ],
};

library.add(glFilterSolid, glFilterRegular);

export const iconMixin = {
    components: {
        Icon: FontAwesomeIcon,
    },
};

export const iconPlugin = {
    install(Vue) {
        Vue.mixin(iconMixin);
    },
};
