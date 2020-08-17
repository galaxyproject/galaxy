import _ from "underscore";

export function templateAddingDatasetsProgressBar() {
    return _.template(
        `<div class="import_text">
                Adding selected datasets to library folder <b><%= _.escape(folder_name) %></b>
            </div>
            <div class="progress">
                <div class="progress-bar progress-bar-import" role="progressbar" aria-valuenow="0" aria-valuemin="0"
                    aria-valuemax="100" style="width: 00%;">
                    <span class="completion_span">0% Complete</span>
                </div>
            </div>`
    );
}
