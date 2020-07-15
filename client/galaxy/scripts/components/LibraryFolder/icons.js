import { faFile, faSave, faFolder } from "@fortawesome/free-regular-svg-icons";
import {
    faTimes,
    faKey,
    faShieldAlt,
    faGlobe,
    faHome,
    faInfoCircle,
    faPlus,
    faSpinner,
    faTrash,
    faBan,
} from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

const tableIcons = [faFile, faFolder, faSpinner, faShieldAlt, faKey, faGlobe, faSave, faTimes, faBan];
const topBarIcons = [faHome, faPlus, faInfoCircle, faTrash];

export function initFolderTableIcons() {
    tableIcons.forEach((icon) => {
        library.add(icon);
    });
}

export function initTopBarIcons() {
    topBarIcons.forEach((icon) => {
        library.add(icon);
    });
}
