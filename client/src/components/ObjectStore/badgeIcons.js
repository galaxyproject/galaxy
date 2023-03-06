/* I can't get this to type properly in type script, so
   handling it here in JavaScript. I get a variant of this
   error (https://github.com/FortAwesome/Font-Awesome/issues/12575).
*/
import { library } from "@fortawesome/fontawesome-svg-core";

import {
    faUserLock,
    faChartLine,
    faBan,
    faCircleNotch,
    faPlug,
    faTachometerAlt,
    faArchive,
    faRecycle,
    faKey,
    faShieldAlt,
    faCloud,
} from "@fortawesome/free-solid-svg-icons";

library.add(
    faUserLock,
    faChartLine,
    faBan,
    faCircleNotch,
    faPlug,
    faTachometerAlt,
    faArchive,
    faRecycle,
    faKey,
    faShieldAlt,
    faCloud
);
