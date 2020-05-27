/**
 * Temporary function used to mount the masthead inside the current application.
 * This function is exposed with the rest of the page-globals in bundledEntries.
 */
import { MastheadState, mountMasthead } from "../../layout/masthead";
import $ from "jquery";

export function initMasthead(config, container) {
    console.log("initMasthead");

    const $masthead = $("#masthead");

    if (config.hide_masthead) {
        $masthead.remove();
    } else {
        if (container) {
            const mastheadState = new MastheadState();
            mountMasthead(container, config, mastheadState);
        }
    }
}
