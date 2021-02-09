/**
 * Presentation models. This is what we feed the components
 * and the crud functions, etc. Goal is to separate persistence
 * and caching from API so it's easier to tweak.
 */

import { Content } from "./Content";

export class Dataset extends Content {
    getUrl(urlType) {
        const { id, file_ext } = this;
        const urls = {
            purge: `datasets/${id}/purge_async`,
            display: `datasets/${id}/display/?preview=True`,
            edit: `datasets/edit?dataset_id=${id}`,
            download: `datasets/${id}/display?to_ext=${file_ext}`,
            report_error: `dataset/errors?id=${id}`,
            rerun: `tool_runner/rerun?id=${id}`,
            show_params: `datasets/${id}/show_params`,
            visualization: "visualization",
            meta_download: `dataset/get_metadata_file?hda_id=${id}&metadata_name=`,
        };
        return urlType in urls ? urls[urlType] : null;
    }

    get canEditName() {
        return this.element_identifier ? false : true;
    }

    get hasData() {
        return this.file_size && this.file_size > 0;
    }

    get hasMetaData() {
        const meta_files = this.meta_files || [];
        return meta_files && meta_files.length > 0;
    }

    get displayLinks() {
        const { display_apps = [], display_types = [] } = this;
        return [...display_apps, ...display_types];
    }

    // determine if a "real" dataset or the abbreviated version returned by a collection api query
    // if it has any of this stuff, it's a nested dataset
    // element_identifier: "M117-ch_2.fq.fastqsanger"
    // element_index: 0
    // element_type: "hda"
    get isFullDataset() {
        return this.element_index === undefined && this.element_index === undefined && this.element_type === undefined;
    }
}
