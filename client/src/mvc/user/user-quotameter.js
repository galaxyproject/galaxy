import $ from "jquery";
import Backbone from "backbone";
import _ from "underscore";
import baseMVC from "mvc/base-mvc";
import _l from "utils/localization";
import { getAppRoot } from "onload/loadConfig";

var logNamespace = "user";
//==============================================================================
/** @class View to display a user's disk/storage usage
 *      either as a progress bar representing the percentage of a quota used
 *      or a simple text element displaying the human readable size used.
 *  @name UserQuotaMeter
 *  @augments Backbone.View
 */
var UserQuotaMeter = Backbone.View.extend(baseMVC.LoggableMixin).extend(
    /** @lends UserQuotaMeter.prototype */ {
        _logNamespace: logNamespace,

        /** Defaults for optional settings passed to initialize */
        options: {
            warnAtPercent: 85,
            errorAtPercent: 100,
            quotaUrl: "https://galaxyproject.org/support/account-quotas/",
        },

        storageDashboardUrl: `${getAppRoot()}storage`,

        /** Set up, accept options, and bind events */
        initialize: function (options) {
            this.log(`${this}.initialize:`, options);
            _.extend(this.options, options);

            //this.bind( 'all', function( event, data ){ this.log( this + ' event:', event, data ); }, this );
            this.listenTo(this.model, "change:quota_percent change:total_disk_usage", this.render);
        },

        /** Re-load user model data from the api */
        update: function (options) {
            this.log(`${this} updating user data...`, options);
            this.model.loadFromApi(this.model.get("id"), options);
            return this;
        },

        /** Is the user over their quota (if there is one)?
         * @returns {Boolean} true if over quota, false if no quota or under quota
         */
        isOverQuota: function () {
            return (
                this.model.get("quota_percent") !== null &&
                this.model.get("quota_percent") >= this.options.errorAtPercent
            );
        },

        /** Render the meter when they have an applicable quota. Will render as a progress bar
         *      with their percentage of that quota in text over the bar.
         *  @fires quota:over when user is over quota (>= this.errorAtPercent)
         *  @fires quota:under when user is under quota
         *  @fires quota:under:approaching when user is >= this.warnAtPercent of their quota
         *  @fires quota:under:ok when user is below this.warnAtPercent
         *  @returns {jQuery} the rendered meter
         */
        _render_quota: function () {
            var modelJson = this.model.toJSON();

            var //prevPercent = this.model.previous( 'quota_percent' ),
                percent = modelJson.quota_percent;

            var //meter = $( UserQuotaMeter.templates.quota( modelJson ) );
                $meter = $(this._templateQuotaMeter(modelJson));

            var $bar = $meter.find(".progress-bar");
            //this.log( this + '.rendering quota, percent:', percent, 'meter:', meter );

            // OVER QUOTA: color the quota bar and show the quota error message
            if (this.isOverQuota()) {
                //this.log( '\t over quota' );
                $bar.attr("class", "progress-bar bg-danger");
                $meter.find(".quota-meter-text").css("color", "white");
                //TODO: only trigger event if state has changed
                this.trigger("quota:over", modelJson);

                // APPROACHING QUOTA: color the quota bar
            } else if (percent >= this.options.warnAtPercent) {
                //this.log( '\t approaching quota' );
                $bar.attr("class", "progress-bar bg-warning");
                //TODO: only trigger event if state has changed
                this.trigger("quota:under quota:under:approaching", modelJson);

                // otherwise, hide/don't use the msg box
            } else {
                $bar.attr("class", "progress-bar bg-success");
                //TODO: only trigger event if state has changed
                this.trigger("quota:under quota:under:ok", modelJson);
            }
            return $meter;
        },

        /** Render the meter when the user has NO applicable quota. Will render as text
         *      showing the human readable sum storage their data is using.
         *  @returns {jQuery} the rendered text
         */
        _render_usage: function () {
            //var usage = $( UserQuotaMeter.templates.usage( this.model.toJSON() ) );
            var usage = $(this._templateUsage(this.model.toJSON()));
            this.log(`${this}.rendering usage:`, usage);
            return usage;
        },

        /** Render either the quota percentage meter or the human readable disk usage
         *      depending on whether the user model has quota info (quota_percent === null -> no quota)
         *  @returns {Object} this UserQuotaMeter
         */
        render: function () {
            //this.log( this + '.rendering' );
            var meterHtml = null;

            // no quota on server ('quota_percent' === null (can be valid at 0)), show usage instead
            this.log(`${this}.model.quota_percent:`, this.model.get("quota_percent"));
            if (this.model.get("quota_percent") === null || this.model.get("quota_percent") === undefined) {
                meterHtml = this._render_usage();

                // otherwise, render percent of quota (and warning, error)
            } else {
                meterHtml = this._render_quota();
                //TODO: add the original text for unregistered quotas
                //tooltip = "Your disk quota is %s.  You can increase your quota by registering a Galaxy account."
            }

            this.$el.html(meterHtml);
            this.$el.find(".quota-meter-text").tooltip();
            return this;
        },

        _templateQuotaMeter: function (data) {
            const title = data.nice_total_disk_usage
                ? `title="Using ${data.nice_total_disk_usage}. Click for details."`
                : "";
            const using = `${_l("Using")} ${data.quota_percent}%`;
            return `<div id="quota-meter" class="quota-meter progress" style="cursor: pointer" onclick="location.href='${this.storageDashboardUrl}';">
    <div class="progress-bar" style="width: ${data.quota_percent}%"></div>
    <div class="quota-meter-text" data-placement="left" ${title}>
        <a>${using}</a>
    </div>
</div>`;
        },

        _templateUsage: function (data) {
            return [
                `<div id="quota-meter" class="quota-meter" style="background-color: transparent; cursor: pointer" onclick="location.href='${this.storageDashboardUrl}';">`,
                '<div class="quota-meter-text" data-placement="left" data-original-title="Click for details." style="color: white">',
                data.nice_total_disk_usage ? _l("Using ") + data.nice_total_disk_usage : "",
                "</div>",
                "</div>",
            ].join("");
        },

        toString: function () {
            return `UserQuotaMeter(${this.model})`;
        },
    }
);

//==============================================================================
export default {
    UserQuotaMeter: UserQuotaMeter,
};
