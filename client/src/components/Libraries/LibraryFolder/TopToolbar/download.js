import $ from "jquery";
import { Toast } from "composables/toast";
import { getAppRoot } from "onload";

function processDownload(url, data, method) {
    //url and data options required
    if (url && data) {
        //data can be string of parameters or array/object
        data = typeof data == "string" ? data : $.param(data);
        //split params into form inputs
        var inputs = "";
        $.each(data.split("&"), function () {
            var pair = this.split("=");
            inputs += `<input type="hidden" name="${pair[0]}" value="${pair[1]}" />`;
        });
        //send request
        $(`<form action="${url}" method="${method || "post"}">${inputs}</form>`)
            .appendTo("body")
            .submit()
            .remove();

        Toast.info("Your download will begin soon.");
    }
}
/**
 * Download selected datasets. Called from the router.
 * @param  {str} format requested archive format
 * @param  dataset_ids requested datasets_ids
 * @param  folder_ids requested folder_ids
 */
export default function download(format, dataset_ids, folder_ids) {
    // function download(format) {
    var url = `${getAppRoot()}api/libraries/datasets/download/${format}`;
    var data = { ld_ids: dataset_ids, folder_ids: folder_ids };
    processDownload(url, data, "get");
}
