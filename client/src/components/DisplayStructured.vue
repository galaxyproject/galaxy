<template>
    <div>
        <!-- eslint-disable-next-line vue/require-v-for-key -->
        <div v-for="error in errorMessages">
            <div class="alert alert-danger" role="alert">{{ error }}</div>
        </div>
        <div v-html="historyTemplate"></div>
    </div>
</template>

<script>
import $ from "jquery";
import { getGalaxyInstance } from "app";
import { getAppRoot } from "onload/loadConfig";
import axios from "axios";
import HDAModel from "mvc/history/hda-model";
import HDAListItemEdit from "mvc/history/hda-li-edit";

export default {
    props: {
        id: {
            type: String,
            required: false,
        },
    },
    data() {
        return {
            historyTemplate: "",
            historyJSON: {},
            // TODO: Error message standardization -- use bootstrap-vue component or the like.
            errorMessages: [],
        };
    },
    created: function () {
        const historyId = this.id;
        let url = "";
        if (historyId !== undefined && historyId !== "" && historyId !== null) {
            url = getAppRoot() + "history/display_structured?id=" + historyId;
        } else {
            url = getAppRoot() + "history/display_structured";
        }
        this.ajaxCall(url);
    },
    updated: function () {
        this.makeHistoryView(this.historyJSON);
    },
    methods: {
        ajaxCall: function (url) {
            axios
                .get(url)
                .then((response) => {
                    this._updateHistoryData(response);
                })
                .catch((e) => {
                    console.error(e);
                    this.errorMessages.push(
                        "Error fetching history data -- reload the page to retry this request.  Please contact an administrator if the problem persists."
                    );
                });
        },
        _updateHistoryData: function (response) {
            const historyItems = response.data;
            this.historyTemplate = historyItems.template;
            this.historyJSON = historyItems.history_json;
        },
        makeHistoryView: function (historyDict) {
            window.hdas = historyDict.map((hda) => {
                const Galaxy = getGalaxyInstance();
                return new HDAListItemEdit.HDAListItemEdit({
                    model: new HDAModel.HistoryDatasetAssociation(hda),
                    el: $("#hda-" + hda.id),
                    linkTarget: "galaxy_main",
                    purgeAllowed: Galaxy.config.allow_user_dataset_purge,
                    logger: Galaxy.logger,
                }).render(0);
            });
            // toggle the body section of each item in the structure
            $(function () {
                $(".workflow, .tool").each((index, element) => {
                    const body = $(element).children(".body");
                    $(element)
                        .children(".header")
                        .click((e) => {
                            body.toggle();
                        })
                        .addClass("clickable");
                });
            });
        },
    },
};
</script>

<style>
.bold {
    font-weight: bold;
}
.light {
    font-weight: lighter;
    color: grey;
}
.right-aligned {
    text-align: right;
}
.clickable {
    cursor: pointer;
}
.workflow {
    border: solid gray 1px;
    margin-bottom: 1%;
}
.workflow > .header {
    background: lightgray;
    padding: 5px 10px;
}
.workflow > .light {
    color: gray;
}
.workflow > .body {
    border-top: solid gray 1px;
}
.workflow > .body > .tool {
    border: 0px;
    margin: 0;
}
div.tool {
    margin-bottom: 5px;
    border: 1px solid gray;
}
.tool > .header {
    padding: 5px 10px;
}
.job-inputs {
    margin: 0px 6px 0px 6px;
    text-align: left;
}
.job-inputs td:nth-child(1) {
    text-align: right;
    font-weight: lighter;
    color: gray;
}
.job-inputs td:nth-child(1):after {
    content: ":";
}
.job-inputs td:nth-child(2) {
    padding-left: 4px;
}
.job-inputs-show {
    float: right;
}
.copied-from {
    border: 1px solid lightgrey;
    border-width: 1px 1px 0px 1px;
    margin-bottom: 5px;
}
.copied-from .header {
    border-bottom: 1px solid lightgrey;
    padding: 5px;
}
.copied-from .header .bold,
.copied-from .header a {
    color: #888;
}
</style>
