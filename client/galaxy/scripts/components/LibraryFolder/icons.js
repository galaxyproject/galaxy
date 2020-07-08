import { faFile } from "@fortawesome/free-regular-svg-icons";
import { faFolder } from "@fortawesome/free-regular-svg-icons";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { faShieldAlt } from "@fortawesome/free-solid-svg-icons";
import { faGlobe } from "@fortawesome/free-solid-svg-icons";
import { faKey } from "@fortawesome/free-solid-svg-icons";
import { faSave } from "@fortawesome/free-regular-svg-icons";
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

const icons = [faFile, faFolder, faSpinner, faShieldAlt, faKey, faGlobe, faSave, faTimes];

export function initFontAwesomeIcons() {
    icons.forEach((icon) => {
        library.add(icon);
    });
}
