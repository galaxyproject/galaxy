/** @class View to display a user's disk/storage usage
 *      either as a progress bar representing the percentage of a quota used
 *      or a simple text element displaying the human readable size used.
 *  @name UserQuotaMeter
 *
 *  @augments Backbone.View
 *  @borrows LoggableMixin#logger as #logger
 *  @borrows LoggableMixin#log as #log
 *  @constructs
 */
var UserQuotaMeter = Backbone.View.extend( LoggableMixin ).extend(
/** @lends UserQuotaMeter.prototype */{
    
    ///** logger used to record this.log messages, commonly set to console */
    //// comment this out to suppress log output
    //logger              : console,

    /** Defaults for optional settings passed to initialize */
    options : {
        warnAtPercent   : 85,
        errorAtPercent  : 100
    },

    /** Set up, accept options, and bind events */
    initialize : function( options ){
        this.log( this + '.initialize:', options );
        _.extend( this.options, options );
        
        //this.bind( 'all', function( event, data ){ this.log( this + ' event:', event, data ); }, this );
        this.model.bind( 'change:quota_percent change:total_disk_usage', this.render, this );
    },

    /** Re-load user model data from the api */
    update : function( options ){
        this.log( this + ' updating user data...', options );
        this.model.loadFromApi( this.model.get( 'id' ), options );
        return this;
    },

    /** Is the user over their quota (if there is one)?
     * @returns {Boolean} true if over quota, false if no quota or under quota
     */
    isOverQuota : function(){
        return ( this.model.get( 'quota_percent' ) !== null
              && this.model.get( 'quota_percent' ) >= this.options.errorAtPercent );
    },

    /** Render the meter when they have an applicable quota. Will render as a progress bar
     *      with their percentage of that quota in text over the bar.
     *  @fires quota:over when user is over quota (>= this.errorAtPercent)
     *  @fires quota:under when user is under quota
     *  @fires quota:under:approaching when user is >= this.warnAtPercent of their quota
     *  @fires quota:under:ok when user is below this.warnAtPercent
     *  @returns {jQuery} the rendered meter
     */
    _render_quota : function(){
        var modelJson = this.model.toJSON(),
            //prevPercent = this.model.previous( 'quota_percent' ),
            percent = modelJson.quota_percent,
            meter = $( UserQuotaMeter.templates.quota( modelJson ) );
        //this.log( this + '.rendering quota, percent:', percent, 'meter:', meter );

        // OVER QUOTA: color the quota bar and show the quota error message
        if( this.isOverQuota() ){
            //this.log( '\t over quota' );
            meter.addClass( 'progress-danger' );
            meter.find( '#quota-meter-text' ).css( 'color', 'white' );
            //TODO: only trigger event if state has changed
            this.trigger( 'quota:over', modelJson );

        // APPROACHING QUOTA: color the quota bar
        } else if( percent >= this.options.warnAtPercent ){
            //this.log( '\t approaching quota' );
            meter.addClass( 'progress-warning' );
            //TODO: only trigger event if state has changed
            this.trigger( 'quota:under quota:under:approaching', modelJson );

        // otherwise, hide/don't use the msg box
        } else {
            meter.addClass( 'progress-success' );
            //TODO: only trigger event if state has changed
            this.trigger( 'quota:under quota:under:ok', modelJson );
        }
        return meter;
    },

    /** Render the meter when the user has NO applicable quota. Will render as text
     *      showing the human readable sum storage their data is using.
     *  @returns {jQuery} the rendered text
     */
    _render_usage : function(){
        var usage = $( UserQuotaMeter.templates.usage( this.model.toJSON() ) );
        this.log( this + '.rendering usage:', usage );
        return usage;
    },

    /** Render either the quota percentage meter or the human readable disk usage
     *      depending on whether the user model has quota info (quota_percent === null -> no quota)
     *  @returns {Object} this UserQuotaMeter
     */
    render : function(){
        //this.log( this + '.rendering' );
        var meterHtml = null;
        
        // no quota on server ('quota_percent' === null (can be valid at 0)), show usage instead
        this.log( this + '.model.quota_percent:', this.model.get( 'quota_percent' ) );
        if( ( this.model.get( 'quota_percent' ) === null )
        ||  ( this.model.get( 'quota_percent' ) === undefined ) ){
            meterHtml = this._render_usage();

        // otherwise, render percent of quota (and warning, error)
        } else {
            meterHtml = this._render_quota();
            //TODO: add the original text for unregistered quotas
            //tooltip = "Your disk quota is %s.  You can increase your quota by registering a Galaxy account."
        }
        
        this.$el.html( meterHtml );
        this.$el.find( '.quota-meter-text' ).tooltip();
        return this;
    },

    toString : function(){
        return 'UserQuotaMeter(' + this.model + ')';
    }
});


//------------------------------------------------------------------------------ TEMPLATES
UserQuotaMeter.templates = {
    quota : Handlebars.templates[ 'template-user-quotaMeter-quota' ],
    usage : Handlebars.templates[ 'template-user-quotaMeter-usage' ]
};
