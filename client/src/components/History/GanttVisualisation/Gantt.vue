<template>
    <CurrentUser v-slot="{ user }">
        <UserHistories v-if="user" v-slot="{ historiesLoading }" :user="user">
            <div>
                <b-alert v-if="historiesLoading || isLoading" class="m-2" variant="info" show>
                    <LoadingSpan message="Loading Gantt Visualization" />
                </b-alert>
                <b-alert v-if="emptyHistory" class="m-2" variant="info" show>
                    <EmptyHistory />
                </b-alert>
                <div class="sticky">
                    <div class="timeButtonsDiv">
                        <button id="QDayView" :disabled="emptyHistory" @click="changeQDayView">Quarter Day View</button>
                        <button id="HDayView" :disabled="emptyHistory" @click="changeHDayView">Half Day View</button>
                        <button id="dayView" :disabled="emptyHistory" @click="changeDayView">Day View</button>
                        <button id="weekView" :disabled="emptyHistory" @click="changeWeekView">Week View</button>
                        <button id="monthView" :disabled="emptyHistory" @click="changeMonthView">Month View</button>
                        <button id="hourView" :disabled="emptyHistory" @click="changeHourView">Hour View</button>
                        <button id="minuteView" :disabled="emptyHistory" @click="changeMinuteView">Minute View</button>
                    </div>
                </div>
                <div>
                    <svg id="gantt"></svg>
                </div>
                <DateTimeModal
                    v-if="openModal"
                    :dateTimeVal="dateTimeVal"
                    :openModal="openModal"
                    @closeModal="closeModal"
                    @changeDate="changeDate" />
            </div>
        </UserHistories>
    </CurrentUser>
</template>

<script>
import Gantt from "../../../../node_modules/frappe-gantt";
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";
import { keyedColorScheme } from "utils/color";
import { useHistoryItemsStore } from "stores/history/historyItemsStore";
import { mapState, mapActions } from "pinia";
import CurrentUser from "components/providers/CurrentUser";
import UserHistories from "components/providers/UserHistories";
import LoadingSpan from "components/LoadingSpan";
import DateTimeModal from "./DateTimeModal.vue";
import EmptyHistory from "./EmptyHistory.vue";
import moment from "moment";

export default {
    name: "Gantt",
    components: {
        LoadingSpan,
        EmptyHistory,
        CurrentUser,
        UserHistories,
        DateTimeModal,
    },
    data() {
        return {
            tasks: [],
            historyId: null,
            accountingArray: [],
            accountingArrayMinutes: [],
            ganttView: "Hour",
            historyItems: [],
            currentlyProcessing: false,
            isLoading: true,
            openModal: false,
            emptyHistory: false,
            dateTimeVal: new Date().toLocaleString("en-GB"),
            start_time: null,
            end_time: null,
        };
    },
    computed: {
        ...mapGetters({ currentHistoryId: "history/currentHistoryId" }),
        ...mapActions(useHistoryItemsStore, ["fetchHistoryItems"]),
        ...mapState(useHistoryItemsStore, ["items"]),
        ...mapState(useHistoryItemsStore, { storeGetHistoryItems: 'getHistoryItems' }),
        history() {
            return this.currentHistoryId;
        },
        historyContent() {
            console.log('got the history content ', this.items[this.historyId])
            return this.items[this.historyId];
        },
    },
    watch: {
        currentHistoryId(newHistoryId, oldHistoryId) {
            if (newHistoryId !== oldHistoryId) {
                // Making currently processing false so that when you switch to a new History, we can re-fetch the historyContents to refresh the GANTT
                this.currentlyProcessing = false;
                this.historyId = newHistoryId;
                if (this.historyId !== undefined) {
                    this.getHistoryItems();
                }
                this.createKeyedColorForButtons();
            }
        },
        historyContent(newContent, oldContent) {
            if (newContent && newContent.length > 0 && !this.currentlyProcessing) {
                this.emptyHistory = false;
                this.historyItems = newContent;
                this.getData();
            } else if (newContent && newContent.length == 0) {
                this.emptyHistory = true;
            }
            this.createKeyedColorForButtons();
        },
        emptyHistory(newEmpty, oldEmpty) {
            if (newEmpty === true) {
                var container = document.getElementsByClassName("gantt");
                if (container) {
                    // We will make .gantt empty so that old data from the visualization is removed
                    this.accountingArray = [];
                    this.accountingArrayMinutes = [];
                    container[0].innerHTML = "";
                }
            }
        },
        ganttView(newval, oldval) {
            if (oldval == "Minute") {
                this.makeGantt();
            }
        },
    },
    mounted() {
        this.getData();
        this.createKeyedColorForButtons();
    },
    methods: {
        ...mapCacheActions(["fetchJobMetricsForDatasetId"]),
        getHistoryItems: async function () {
            if (this.historyId) {
                await this.fetchHistoryItems( this.historyId, "", 0 );
            }
        },
        changeDate: function (value, status) {
            this.dateTimeVal = value;
            if (status == "confirmed") {
                this.start_time = moment(value).format("YYYY-MM-DD HH:mm:ss");
                this.end_time = moment(value).add(10, "minutes").format("YYYY-MM-DD HH:mm:ss");
                if (this.start_time && this.end_time) {
                    this.isLoading = true;
                    this.accountingArrayMinutes = this.accountingArray.filter((entry) => {
                        if (moment(this.end_time).isBefore(moment(entry.endTime))) {
                            this.end_time = moment(entry.endTime).format("YYYY-MM-DD HH:mm:ss");
                        }
                        return moment(entry.startTime).isBetween(moment(this.start_time), moment(this.end_time));
                    });
                    this.makeGantt();
                    this.gantt.change_view_mode("Minute");
                }
            }
        },
        makeGantt: function () {
            var entries = [];
            if (this.ganttView == "Minute") {
                this.accountingArrayMinutes.map((row, idx) => {
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
            } else {
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
            }
            this.isLoading = false;
            if (entries.length > 0) {
                this.gantt = new Gantt("#gantt", entries, {
                    view_mode: "Day",
                    view_modes: ["Quarter Day", "Half Day", "Day", "Week", "Month", "Hour", "Minute"],
                    arrow_curve: 14,
                    date_format: "DD-MM-YYYY",
                    popup_trigger: "mouseover",
                    start_time: this.start_time,
                    end_time: this.end_time,
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
                      </div>`;
                    },
                });
            }
        },
        getData: async function () {
            this.isLoading = true;
            this.currentlyProcessing = true;
            this.historyId = this.history;
            this.accountingArray = [];
            this.historyItems = this.storeGetHistoryItems( this.historyId, "" );
            if (this.historyItems.length == 0) {
                this.currentlyProcessing = false;
                this.getHistoryItems();
            }
            if (this.historyItems && this.historyItems.length > 0) {
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
                if (this.accountingArray.length > 0) {
                    this.currentlyProcessing = false;
                    this.makeGantt();
                }
            }
        },
        closeModal() {
            this.openModal = false;
        },
        changeQDayView: function () {
            this.ganttView = "Quarter Day";
            this.gantt.change_view_mode("Quarter Day");
        },
        changeHDayView: function () {
            this.ganttView = "Half Day";
            this.gantt.change_view_mode("Half Day");
        },
        changeDayView: function () {
            this.ganttView = "Day";
            this.gantt.change_view_mode("Day");
        },
        changeWeekView: function () {
            this.ganttView = "Week";
            this.gantt.change_view_mode("Week");
        },
        changeMonthView: function () {
            this.ganttView = "Month";
            this.gantt.change_view_mode("Month");
        },
        changeHourView: function () {
            this.ganttView = "Hour";
            this.gantt.change_view_mode("Hour");
        },
        changeMinuteView: function () {
            this.ganttView = "Minute";
            this.openModal = true;
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
    if (!document.styleSheets) {
        return;
    }
    if (document.getElementsByTagName("head").length == 0) {
        return;
    }

    var styleSheet;
    var mediaType;

    if (document.styleSheets.length > 0) {
        for (var i = 0, l = document.styleSheets.length; i < l; i++) {
            if (document.styleSheets[i].disabled) {
                continue;
            }
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

            if (typeof styleSheet !== "undefined") {
                break;
            }
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
        for (i = 0, l = styleSheet.rules.length; i < l; i++) {
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
        for (i = 0; i < styleSheetLength; i++) {
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
.sticky {
    position: fixed;
}
.gantt-container {
    position: inherit !important;
}
.gantt {
    margin-top: 50px;
}
.popup-wrapper {
    margin-top: 65px;
    margin-left: 15px;
    margin-right: 15px;
}
</style>
