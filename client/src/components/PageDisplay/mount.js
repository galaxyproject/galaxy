/**
 * Endpoint for mounting PageDisplay from non-Vue environment (annotated DOMs).
 */
import $ from "jquery";
import Vue from "vue";
import PageDisplay from "./PageDisplay.vue";

export const mountPageDisplay = (propsData = {}) => {
    $("#page-display-content").each((index, el) => {
        const pageId = $(el).attr("page_id");
        const component = Vue.extend(PageDisplay);
        propsData.pageId = pageId;
        return new component({ propsData: propsData }).$mount(el);
    });
};
