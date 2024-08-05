import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheckSquare, faFile, faFolder, faSave, faSquare } from "@fortawesome/free-regular-svg-icons";
import {
    faAngleDoubleLeft,
    faBan,
    faGlobe,
    faHome,
    faKey,
    faMinusSquare,
    faPencilAlt,
    faShieldAlt,
    faSpinner,
    faTimes,
    faTrash,
    faUnlock,
    faUsers,
} from "@fortawesome/free-solid-svg-icons";

const tableIcons = [
    faFile,
    faFolder,
    faSpinner,
    faShieldAlt,
    faKey,
    faGlobe,
    faSave,
    faTimes,
    faBan,
    faUnlock,
    faPencilAlt,
    faUsers,
    faCheckSquare,
    faSquare,
    faMinusSquare,
];

const manageIcons = [faAngleDoubleLeft, faSave, faFile];
const librariesIcons = [faGlobe, faPencilAlt, faSave, faTimes, faTrash, faUsers, faHome, faUnlock];

export function initFolderTableIcons() {
    tableIcons.forEach((icon) => library.add(icon));
}

export function initPermissionsIcons() {
    manageIcons.forEach((icon) => library.add(icon));
}
export function initLibrariesIcons() {
    librariesIcons.forEach((icon) => library.add(icon));
}
