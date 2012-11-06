// strange view that spans two frames: renders to two separate elements based on a User's disk usage:
//  a quota/usage bar (curr. masthead), and
//  an over-quota message (curr. history panel)

// for now, keep the view in the history panel (where the message is), but render ALSO to the masthead

var UserQuotaMeter = BaseView.extend( LoggableMixin ).extend({
    //logger          : console,

    options : {
        warnAtPercent   : 85,
        errorAtPercent  : 100,

        // the quota/usage bar is in the masthead
        meterDocument   : window.top.document,
        containerSelector : '.quota-meter-container',
        meterSelector   : '#quota-meter',
        barSelector     : '#quota-meter-bar',
        textSelector    : '#quota-meter-text',

        // the quota message currently displays in the history panel
        msgDocument     : ( top.frames.galaxy_history )?( top.frames.galaxy_history.document )
                                                       :( top.document ),
        msgSelector     : '#quota-message-container',

        warnClass       : 'quota-meter-bar-warn',
        errorClass      : 'quota-meter-bar-error',
        usageTemplate   : 'Using <%= nice_total_disk_usage %>',
        quotaTemplate   : 'Using <%= quota_percent %>%',
        meterTemplate   : '', // see where I'm going?
        animationSpeed  : 'fast'
    },

    initialize : function( options ){
        this.log( this + '.initialize:', options );
        
        _.extend( this.options, options );
        
        //this.bind( 'all', function( event, data ){ this.log( this + ' event:', event, data ); }, this );
        this.model.bind( 'change:quota_percent change:total_disk_usage', this.render, this );
    },

    update : function( options ){
        this.log( this + ' updating user data...', options );
        this.model.loadFromApi( this.model.get( 'id' ), options );
        return this;
    },

    isOverQuota : function(){
        return ( this.model.get( 'quota_percent' ) !== null
              && this.model.get( 'quota_percent' ) >= this.options.errorAtPercent );
    },

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

    _render_usage : function(){
        var usage = $( UserQuotaMeter.templates.usage( this.model.toJSON() ) );
        this.log( this + '.rendering usage:', usage );
        return usage;
    },

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
        }
        
        this.$el.html( meterHtml );
        //this.log( this + '.$el:', this.$el );
        return this;
    },

    toString : function(){
        return 'UserQuotaMeter(' + this.model + ')';
    }
});
UserQuotaMeter.templates = {
    quota : Handlebars.templates[ 'template-user-quotaMeter-quota' ],
    usage : Handlebars.templates[ 'template-user-quotaMeter-usage' ]
};
