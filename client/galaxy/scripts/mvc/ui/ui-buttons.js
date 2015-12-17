/** This class contains all button views.
*/
define(['utils/utils'], function( Utils ) {
    /** This renders the default button which is used e.g. at the bottom of the upload modal.
    */
    var ButtonBase = Backbone.View.extend({
        initialize: function( options ) {
            this.options = Utils.merge( options, {
                id          : Utils.uid(),
                title       : '',
                floating    : 'right',
                icon        : '',
                cls         : 'ui-button btn btn-default',
                cls_wait    : 'btn btn-info'
            } );
            this.setElement( this._template( this.options ) );
            var self = this;
            $( this.el ).on( 'click' , function() {
                $( '.tooltip' ).hide();
                if ( options.onclick && !self.disabled ) {
                    options.onclick();
                }
            } );
            $( this.el ).tooltip( { title: options.tooltip, placement: 'bottom' } );
        },

        // disable
        disable: function() {
            this.$el.addClass( 'disabled' );
            this.disabled = true;
        },

        // enable
        enable: function() {
            this.$el.removeClass( 'disabled' );
            this.disabled = false;
        },

        // show spinner
        wait: function() {
            this.$el.removeClass( this.options.cls ).addClass( this.options.cls_wait ).prop( 'disabled', true );
            this.$( '.icon' ).removeClass( this.options.icon ).addClass( 'fa-spinner fa-spin' );
            this.$( '.title' ).html( 'Sending...' );
        },

        // hide spinner
        unwait: function() {
            this.$el.removeClass( this.options.cls_wait ).addClass( this.options.cls ).prop( 'disabled', false );
            this.$( '.icon' ).removeClass( 'fa-spinner fa-spin' ).addClass( this.options.icon );
            this.$( '.title' ).html( this.options.title );
        },

        // template
        _template: function( options ) {
            var str =   '<button id="' + options.id + '" type="submit" style="float: ' + options.floating + ';" type="button" class="' + options.cls + '">';
            if (options.icon) {
                str +=      '<i class="icon fa ' + options.icon + '"/>&nbsp;';
            }
            str +=          '<span class="title">' + options.title + '</span>' +
                        '</button>';
            return str;
        }
    });

    /** This button allows the right-click/open-in-new-tab feature, its used e.g. for panel buttons.
    */
    var ButtonLink = ButtonBase.extend({
        initialize: function( options ) {
            ButtonBase.prototype.initialize.call( this, options );
        },
        _template: function( options ) {
            return  '<a id="' + options.id + '" class="' + options.cls + '" href="' + ( options.href || 'javascript:void(0)' ) + '"' +
                        ' title="' + options.title + '" target="' + ( options.target || '_top' ) + '">' + '<span class="' + options.icon + '"/>' +
                    '</a>';
        }
    });

    /** The check button is used in the tool form and allows to distinguish between multiple states e.g. all, partially and nothing selected.
    */
    var ButtonCheck = Backbone.View.extend({
        initialize: function( options ) {
            // configure options
            this.options = Utils.merge(options, {
                title : 'Select/Unselect all',
                icons : ['fa fa-square-o', 'fa fa-minus-square-o', 'fa fa-check-square-o'],
                value : 0
            });

            // create new element
            this.setElement( this._template() );
            this.$title = this.$( '.title' );
            this.$icon  = this.$( '.icon' );

            // set initial value
            this.value( this.options.value );

            // set title
            this.$title.html( this.options.title );

            // add event handler
            var self = this;
            this.$el.on('click', function() {
                self.current = ( self.current === 0 && 2 ) || 0;
                self.value( self.current );
                self.options.onclick && self.options.onclick();
            });
        },

        /* Sets a new value and/or returns the current value.
        * @param{Integer}   new_val - Set a new value 0=unchecked, 1=partial and 2=checked.
        * OR:
        * @param{Integer}   new_val - Number of selected options.
        * @param{Integer}   total   - Total number of available options.
        */
        value: function ( new_val, total ) {
            if ( new_val !== undefined ) {
                if ( total ) {
                    if ( new_val !== 0 ) {
                        new_val = ( new_val !== total ) && 1 || 2;
                    }
                }
                this.current = new_val;
                this.$icon.removeClass()
                          .addClass( 'icon' )
                          .addClass( this.options.icons[ new_val ] );
                this.options.onchange && this.options.onchange( new_val );
            }
            return this.current;
        },

        /** Template containing the check button and the title
        */
        _template: function() {
            return  '<div class="ui-button-check" >' +
                        '<span class="icon"/>' +
                        '<span class="title"/>' +
                    '</div>';
        }
    });

    /** This renders a differently styled, more compact button version.
        TODO: Consolidate with icon-button.js and/or button-default.js.
    */
    var ButtonIcon = Backbone.View.extend({
        initialize : function( options ) {
            // get options
            this.options = Utils.merge( options, {
                id          : Utils.uid(),
                title       : '',
                floating    : 'right',
                cls         : 'ui-button-icon',
                icon        : '',
                tooltip     : '',
                onclick     : null
            });

            // create new element
            this.setElement( this._template( this.options ) );

            // link button element
            this.$button = this.$el.find( '.button' );

            // add event
            var self = this;
            $(this.el).on('click', function() {
                // hide all tooltips
                $( '.tooltip' ).hide();

                // execute onclick callback
                if ( options.onclick && !self.disabled ) {
                    options.onclick();
                }
            });

            // add tooltip
            this.$button.tooltip( { title: options.tooltip, placement: 'bottom' } );
        },

        // disable
        disable: function() {
            this.$button.addClass( 'disabled' );
            this.disabled = true;
        },

        // enable
        enable: function() {
            this.$button.removeClass( 'disabled' );
            this.disabled = false;
        },

        // change icon
        setIcon: function(icon_cls) {
            this.$('i').removeClass( this.options.icon ).addClass( icon_cls );
            this.options.icon = icon_cls;
        },

        // template
        _template: function( options ) {
            // width
            var width = '';
            if ( options.title ) {
                width = 'width: auto;';
            }

            // string
            var str =   '<div id="' + options.id + '" style="float: ' + options.floating + '; ' + width + '" class="' + options.cls + '">' +
                            '<div class="button">';
            if (options.title) {
                str +=          '<i class="icon fa ' + options.icon + '"/>&nbsp;' +
                                '<span class="title">' + options.title + '</span>';
            } else {
                str +=          '<i class="icon fa ' + options.icon + '"/>';
            }
            str +=          '</div>' +
                        '</div>';
            return str;
        }
    });

    /** This class creates a button with dropdown menu. It extends the functionality of the Ui.ButtonIcon class.
        TODO: Consolidate class, use common base class
    */
    var ButtonMenu = Backbone.View.extend({
        // optional sub menu
        $menu: null,

        // initialize
        initialize: function ( options ) {
            // get options
            this.options = Utils.merge( options, {
                // same as Ui.ButtonIcon
                id              : '',
                title           : '',
                floating        : 'right',
                pull            : 'right',
                icon            : null,
                onclick         : null,
                cls             : 'ui-button-icon ui-button-menu',
                tooltip         : '',
                
                // additional options
                target          : '',
                href            : '',
                onunload        : null,
                visible         : true,
                tag             : ''
            } );

            // add template for tab
            this.setElement( $( this._template( this.options ) ) );

            // find root
            var $root = $( this.el ).find( '.root' );

            // link head
            var self = this;
            $root.on( 'click', function( e ) {
                // hide all tooltips
                $( '.tooltip' ).hide();

                // prevent default
                e.preventDefault();

                // add click event
                if( self.options.onclick ) {
                    self.options.onclick();
                }
            });

            // visiblity
            if ( !this.options.visible )
                this.hide();

            // add tooltip
            $root.tooltip( { title: options.tooltip, placement: 'bottom' } );
        },

        // show
        show: function() {
            $( this.el ).show();
        },

        // hide
        hide: function() {
            $( this.el ).hide();
        },

        // add menu item
        addMenu: function ( options ) {
            // menu option defaults
            var menuOptions = {
                title       : '',
                target      : '',
                href        : '',
                onclick     : null,
                divider     : false,
                icon        : null,
                cls         : 'button-menu btn-group'
            }

            // get options
            menuOptions = Utils.merge( options, menuOptions );

            // check if submenu element is available
            if ( !this.$menu ) {
                // insert submenu element into root
                $( this.el ).append( this._templateMenu() );

                // update element link
                this.$menu = $( this.el ).find( '.menu' );
            }

            // create
            var $item = $( this._templateMenuItem( menuOptions ) );

            // add events
            $item.on( 'click', function( e ) {
                if( menuOptions.onclick ) {
                    e.preventDefault();
                    menuOptions.onclick();
                }
            });

            // append menu
            this.$menu.append( $item );

            // append divider
            if ( menuOptions.divider ) {
                this.$menu.append( $( this._templateDivider() ) );
            }
        },

        // fill template header
        _templateMenuItem: function ( options ) {
            var tmpl =  '<li>' +
                            '<a class="dropdown-item" href="' + options.href + '" target="' + options.target + '" ';
            if ( options.download ) {
                tmpl +=         'download="' + options.download + '"';
            }
            tmpl +=         '>';
            if ( options.icon ) {
                tmpl +=         '<i class="fa ' + options.icon + '"/>';
            }
            tmpl +=             ' ' + options.title +
                            '</a>' +
                        '</li>';
            return tmpl;
        },

        // fill template header
        _templateMenu: function () {
            return '<ul class="menu dropdown-menu pull-' + this.options.pull + '" role="menu"/>';
        },

        _templateDivider: function() {
            return '<li class="divider"/>';
        },

        // element
        _template: function(options) {
            // TODO: width/margin should be set in css
            var width = '';
            var margin = '';
            if ( options.title ) {
                width = 'width: auto;';
            } else {
                margin = 'margin: 0px;';
            }
            var str =   '<div id="' + options.id + '" style="float: ' + options.floating + '; ' + width + '" class="dropdown ' + options.cls + '">' +
                            '<div class="root button dropdown-toggle" data-toggle="dropdown" style="' + margin + '">' +
                                '<i class="icon fa ' + options.icon + '"/>';
            if ( options.title ) {
                str +=          '&nbsp;<span class="title">' + options.title + '</span>';
            }
            str +=          '</div>' +
                        '</div>';
            return str;
        }
    });

    return {
        ButtonDefault   : ButtonBase,
        ButtonLink      : ButtonLink,
        ButtonIcon      : ButtonIcon,
        ButtonCheck     : ButtonCheck,
        ButtonMenu      : ButtonMenu
    }
});
