/**
 * Temporary function used to mount the masthead inside the current application.
 * This function is exposed with the rest of the page-globals in bundledEntries.
 */
// import Vue from "vue";
// import Masthead from "./Masthead";
import Masthead from "../../layout/masthead";
import $ from "jquery";

export function initMasthead(config, container) {
    console.log("initMasthead");

    const masthead = new Masthead.View(config);
    masthead.render();

    const $masthead = $("#masthead");

    if (config.hide_masthead) {
        $masthead.remove();
    } else {
        if (container) {
            $(container).replaceWith(masthead.el);
        }
    }

    // const Component = Vue.extend(Masthead);
    // return new Component({
    //     props: Object.keys(config),
    //     propsData: config,
    //     el: container
    // });
}
