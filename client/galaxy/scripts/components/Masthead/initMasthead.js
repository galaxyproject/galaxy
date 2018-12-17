/**
 * Temporary function used to mount the masthead inside the current application.
 * This function is exposed with the rest of the page-globals in bundledEntries.
 */
import Vue from "vue";
import Masthead from "components/Masthead";

export function initMasthead(config, container) {
    console.log("initMasthead");
    let Component = Vue.extend(Masthead);
    return new Component({
        props: Object.keys(config),
        propsData: config,
        el: container
    });
}
