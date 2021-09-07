import Vue from "vue";
import QuotaUsageDialog from "./QuotaUsageDialog";

export function showQuotaDialog(options = {}) {
    const instance = Vue.extend(QuotaUsageDialog);
    const vm = document.createElement("div");
    document.body.appendChild(vm);
    new instance({
        propsData: options,
    }).$mount(vm);
}
