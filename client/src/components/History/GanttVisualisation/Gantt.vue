<template>
    <div>
        <svg id="gantt"></svg>
        <div class="sticky">
            <button id="QDayView" @click="changeQDayView">Quarter Day View</button>
            <button id="HDayView" @click="changeHDayView">Half Day View</button>
            <button id="dayView" @click="changeDayView">Day View</button>
            <button id="weekView" @click="changeWeekView">Week View</button>
            <button id="monthView" @click="changeMonthView">Month View</button>
            <button id="hourView" @click="changeHourView">Hour View</button>
            <button id="minuteView" @click="changeMinuteView">Minute View</button>
            <button class="btn btn-info" @click="showModal">show modal</button>
            <DateTimeModal v-if="openModal" @closeModal="closeModal" :openModal="openModal" :dateTimeVal="dateTimeVal" @changeDate="changeDate" />
        </div>
    </div>
</template>

<script>
import Gantt from "../../../../node_modules/frappe-gantt";
import store from "../../../store";
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";
import { keyedColorScheme } from "utils/color";
import DateTimeModal from './DateTimeModal.vue'

export default {
    name: "Gantt",
    data() {
        return {
            tasks: [],
            historyId: null,
            accountingArray: [],
            historyItems: [],
            currentlyProcessing: false,
            openModal: false,
            dateTimeVal: new Date().toLocaleString('en-GB'),
        };
    },
    components : { DateTimeModal },
    computed: {
        ...mapGetters({ currentHistoryId: "history/currentHistoryId" }),
        history() {
            return this.currentHistoryId;
        },
        historyContent() {
            return this.$store.state.historyItems.items[this.historyId];
        },
    },
    watch: {
        currentHistoryId(newHistoryId, oldHistoryId) {
            if (newHistoryId !== oldHistoryId) {
                // Making currently processing false so that when you switch to a new History, we can re-fetch the historyContents to refresh the GANTT
                this.currentlyProcessing = false
                this.historyId = newHistoryId;
                // this.accountingArray = [];
                if (this.historyId !== undefined) {
                    this.getHistoryItems();
                }
            }
        },
        historyContent(newContent, oldContent) {
            if ( newContent && !this.currentlyProcessing ) {
                this.historyItems = newContent;
                this.getData();
            }
        },
    },
    mounted() {
        this.getData();
        this.createKeyedColorForButtons();
    },
    methods: {
        ...mapCacheActions(["fetchJobMetricsForDatasetId", "fetchHistoryItems"]),
        getHistoryItems: async function () {
            if (this.historyId) {
                await this.fetchHistoryItems({ historyId: this.historyId, filterText: "", offset: 0 });
            }
        },
        changeDate: function (value) {
          this.dateTimeVal = value
        },
        makeGantt: function () {
            var entries = [];
            this.accountingArray.map((row, idx) => {
                createClassWithCSS(
                    `.class-${row["id"]} .bar-progress`,
                    `fill : ${keyedColorScheme(`random-${row["label"]}`)["primary"]} !important`
                );
                entries.push({
                    id: idx.toString(),
                    job_id: row["id"],
                    name: row["label"],
                    start: row["startTime"],
                    end: row["endTime"],
                    progress: 100,
                    custom_class: `class-${row["id"]}`,
                });
            });
            this.gantt = new Gantt("#gantt", entries, {
                view_mode: "Day",
                view_modes: ["Quarter Day", "Half Day", "Day", "Week", "Month", "Hour", "Minute"],
                arrow_curve: 14,
                date_format: "YYYY-MM-DD",
                popup_trigger: "mouseover",
                custom_popup_html: function (task) {
                return `
                <div class="popover-container">
                <div class="popover-header">
                    ${task.job_id}: ${task.name}  
                </div>
                <div class="popover-body">
                    Started At: ${task.start}
                    <br>
                    Finished At: ${task.end}
                </div>  
                </div>
            `;
        },
    });
},
        getData: async function () {
            this.currentlyProcessing = true
            this.historyId = this.history;
            this.accountingArray = []
            this.historyItems = store.getters.getHistoryItems({ historyId: this.historyId, filterText: "" });
            if (this.historyItems.length == 0) {
                this.currentlyProcessing = false
                this.getHistoryItems();
            }
            if( this.historyItems && this.historyItems.length > 0) {
                    for await (const job of this.historyItems) {
                    var Accounting = {};
                      if (job.id) {
                        await this.fetchJobMetricsForDatasetId({ datasetId: job.id, datasetType: "hda" });
                        const metrics = await this.$store.state?.jobMetrics?.jobMetricsByHdaId[`${job.id}`];
                        if (metrics && metrics[1] && metrics[2]) {
                            Accounting = {
                                label: job.name,
                                id: job.hid,
                                jobid: job.id,
                                startTime: metrics[1].value,
                                endTime: metrics[2].value,
                            };
                            this.accountingArray.push(Accounting);
                        }
                      }
                    }
                    if(this.accountingArray.length > 0) {
                        this.currentlyProcessing = false
                        this.makeGantt()
                    }
            }
        },
        closeModal() {
            this.openModal = false
        },
        showModal() {
            this.openModal = true;
        },
        changeQDayView: function () {
            this.gantt.change_view_mode("Quarter Day");
        },
        changeHDayView: function () {
            this.gantt.change_view_mode("Half Day");
        },
        changeDayView: function () {
            this.gantt.change_view_mode("Day");
        },
        changeWeekView: function () {
            this.gantt.change_view_mode("Week");
        },
        changeMonthView: function () {
            this.gantt.change_view_mode("Month");
        },
        changeHourView: function () {
            this.gantt.change_view_mode("Hour");
        },
        changeMinuteView: function () {
            this.dateTime = true;
            this.gantt.change_view_mode("Minute");
        },
        createKeyedColorForButtons: function () {
            createClassWithCSS(
                ".QDayView",
                `background : ${keyedColorScheme("QDayView")["primary"]}; border-color : ${
                    keyedColorScheme("QDayView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("QDayView").className = "QDayView";
            createClassWithCSS(
                ".HDayView",
                `background : ${keyedColorScheme("HDayView")["primary"]}; border-color : ${
                    keyedColorScheme("HDayView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("HDayView").className = "HDayView";
            createClassWithCSS(
                ".dayView",
                `background : ${keyedColorScheme("dayView")["primary"]}; border-color : ${
                    keyedColorScheme("dayView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("dayView").className = "dayView";
            createClassWithCSS(
                ".weekView",
                `background : ${keyedColorScheme("weekView")["primary"]}; border-color : ${
                    keyedColorScheme("weekView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("weekView").className = "weekView";
            createClassWithCSS(
                ".monthView",
                `background : ${keyedColorScheme("monthView")["primary"]}; border-color : ${
                    keyedColorScheme("monthView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("monthView").className = "monthView";
            createClassWithCSS(
                ".hourView",
                `background : ${keyedColorScheme("hourView")["primary"]}; border-color : ${
                    keyedColorScheme("hourView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("hourView").className = "hourView";
            createClassWithCSS(
                ".minuteView",
                `background : ${keyedColorScheme("minuteView")["primary"]}; border-color : ${
                    keyedColorScheme("minuteView")["darker"]
                } ; color :"black"`
            );
            document.getElementById("minuteView").className = "minuteView";
        },
    },
};

function createClassWithCSS(selector, style) {
    if (!document.styleSheets) return;
    if (document.getElementsByTagName("head").length == 0) return;

    var styleSheet, mediaType;

    if (document.styleSheets.length > 0) {
        for (var i = 0, l = document.styleSheets.length; i < l; i++) {
            if (document.styleSheets[i].disabled) continue;
            var media = document.styleSheets[i].media;
            mediaType = typeof media;

            if (mediaType === "string") {
                if (media === "" || media.indexOf("screen") !== -1) {
                    styleSheet = document.styleSheets[i];
                }
            } else if (mediaType == "object") {
                if (media.mediaText === "" || media.mediaText.indexOf("screen") !== -1) {
                    styleSheet = document.styleSheets[i];
                }
            }

            if (typeof styleSheet !== "undefined") break;
        }
    }

    if (typeof styleSheet === "undefined") {
        var styleSheetElement = document.createElement("style");
        styleSheetElement.type = "text/css";
        document.getElementsByTagName("head")[0].appendChild(styleSheetElement);

        for (i = 0; i < document.styleSheets.length; i++) {
            if (document.styleSheets[i].disabled) {
                continue;
            }
            styleSheet = document.styleSheets[i];
        }

        mediaType = typeof styleSheet.media;
    }

    if (mediaType === "string") {
        for (var i = 0, l = styleSheet.rules.length; i < l; i++) {
            if (
                styleSheet.rules[i].selectorText &&
                styleSheet.rules[i].selectorText.toLowerCase() == selector.toLowerCase()
            ) {
                styleSheet.rules[i].style.cssText = style;
                return;
            }
        }
        styleSheet.addRule(selector, style);
    } else if (mediaType === "object") {
        var styleSheetLength = styleSheet.cssRules ? styleSheet.cssRules.length : 0;
        for (var i = 0; i < styleSheetLength; i++) {
            if (
                styleSheet.cssRules[i].selectorText &&
                styleSheet.cssRules[i].selectorText.toLowerCase() == selector.toLowerCase()
            ) {
                styleSheet.cssRules[i].style.cssText = style;
                return;
            }
        }
        styleSheet.insertRule(selector + "{" + style + "}", styleSheetLength);
    }
}
</script>

<style>
.popover-container {
    width: max-content;
}

.popover-header {
    padding: 0.5rem 1rem;
    margin-bottom: 0;
    border: 1px solid black;
    background-color: #948f8fe2;
    color: white;
    border-top-left-radius: calc(0.3rem - 1px);
    border-top-right-radius: calc(0.3rem - 1px);
}

.popover-body {
    padding: 1rem 1rem;
    color: #212529;
    background-color: white;
    border: 1px solid;
}

.gantt .tick {
    stroke: #666;
}
.gantt {
    margin-top: 50px;
}
.sticky {
    position: fixed;
}
.modal-mask {
    position: fixed;
    z-index: 10000;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    display: table;
}

.modal-wrapper {
    display: table-cell;
    vertical-align: middle;
}
.modal-dialog,
.modal-content {
    /* 80% of window height */
    height: 70%;
}
.gantt-container{
    position: inherit !important;
}
</style>
