/** Renders the color picker used e.g. in the tool form **/
define(['utils/utils'], function( Utils ) {
    return Backbone.View.extend({
        colors: {
            standard: ['c00000','ff0000','ffc000','ffff00','92d050','00b050','00b0f0','0070c0','002060','7030a0'],
            base    : ['ffffff','000000','eeece1','1f497d','4f81bd','c0504d','9bbb59','8064a2','4bacc6','f79646'],
            theme   :[['f2f2f2','7f7f7f','ddd9c3','c6d9f0','dbe5f1','f2dcdb','ebf1dd','e5e0ec','dbeef3','fdeada'],
                      ['d8d8d8','595959','c4bd97','8db3e2','b8cce4','e5b9b7','d7e3bc','ccc1d9','b7dde8','fbd5b5'],
                      ['bfbfbf','3f3f3f','938953','548dd4','95b3d7','d99694','c3d69b','b2a2c7','92cddc','fac08f'],
                      ['a5a5a5','262626','494429','17365d','366092','953734','76923c','5f497a','31859b','e36c09'],
                      ['7f7f7e','0c0c0c','1d1b10','0f243e','244061','632423','4f6128','3f3151','205867','974806']]
        },

        initialize : function( options ) {
            this.options = Utils.merge( options, {} );
            this.setElement( this._template() );
            this.$panel = this.$( '.ui-color-picker-panel' );
            this.$view = this.$( '.ui-color-picker-view' );
            this.$value = this.$( '.ui-color-picker-value' );
            this.$header = this.$( '.ui-color-picker-header' );
            this._build();
            this.visible = false;
            this.value( this.options.value );
            this.$boxes = this.$( '.ui-color-picker-box' );
            var self = this;
            this.$boxes.on( 'click', function() {
                self.value( $( this ).css( 'background-color' ) );
                self.$header.trigger( 'click' );
            } );
            this.$header.on( 'click', function() {
                self.visible = !self.visible;
                if ( self.visible ) {
                    self.$view.fadeIn( 'fast' );
                } else {
                    self.$view.fadeOut( 'fast' );
                }
            } );
        },

        /** Get/set value */
        value : function ( new_val ) {
            if ( new_val !== undefined && new_val !== null ) {
                this.$value.css( 'background-color', new_val );
                this.$( '.ui-color-picker-box' ).empty();
                this.$( this._getValue() ).html( this._templateCheck() );
                this.options.onchange && this.options.onchange( new_val );
            }
            return this._getValue();
        },

        /** Get value from dom */
        _getValue: function() {
            var rgb = this.$value.css( 'background-color' );
            rgb = rgb.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
            if ( rgb ) {
                function hex( x ) {
                    return ( '0' + parseInt( x ).toString( 16 ) ).slice( -2 );
                }
                return '#' + hex( rgb[ 1] ) + hex( rgb[ 2 ] ) + hex( rgb[ 3 ] );
            } else {
                return null;
            }
        },

        /** Build color panel */
        _build: function() {
            var $content = this._content({
                label       : 'Theme Colors',
                colors      : this.colors.base,
                padding     : 10
            });
            for ( var i in this.colors.theme ) {
                var line_def = {};
                if ( i == 0 ) {
                    line_def[ 'bottom' ] = true;
                } else {
                    if ( i != this.colors.theme.length - 1 ) {
                        line_def[ 'top' ]     = true;
                        line_def[ 'bottom' ]  = true;
                    } else {
                        line_def[ 'top' ]     = true;
                        line_def[ 'padding' ] = 5;
                    }
                }
                line_def[ 'colors' ] = this.colors.theme[ i ];
                this._content( line_def );
            }
            this._content({
                label       : 'Standard Colors',
                colors      : this.colors.standard,
                padding     : 5
            });
        },

        /** Create content */
        _content: function( options ) {
            var label       = options.label;
            var colors      = options.colors;
            var padding     = options.padding;
            var top         = options.top;
            var bottom      = options.bottom;
            var $content = $( this._templateContent() );
            var $label = $content.find( '.label' );
            if ( options.label ) {
                $label.html( options.label );
            } else {
                $label.hide();
            }
            var $line = $content.find( '.line' );
            this.$panel.append( $content );
            for ( var i in colors ) {
                var $box = $( this._templateBox( colors[ i ] ) );
                if ( top ) {
                    $box.css( 'border-top', 'none' );
                    $box.css( 'border-top-left-radius', '0px' );
                    $box.css( 'border-top-right-radius', '0px' );
                }
                if ( bottom ) {
                    $box.css( 'border-bottom', 'none' );
                    $box.css( 'border-bottom-left-radius', '0px' );
                    $box.css( 'border-bottom-right-radius', '0px' );
                }
                $line.append( $box );
            }
            if (padding) {
                $line.css( 'padding-bottom', padding );
            }
            return $content;
        },

        /** Check icon */
        _templateCheck: function() {
            return  '<div class="ui-color-picker-check fa fa-check"/>';
        },

        /** Content template */
        _templateContent: function() {
            return  '<div class="ui-color-picker-content">' +
                        '<div class="label"/>' +
                        '<div class="line"/>' +
                    '</div>';
        },

        /** Box template */
        _templateBox: function( color ) {
            return '<div id="' + color + '" class="ui-color-picker-box" style="background-color: #' + color + ';"/>';
        },

        /** Main template */
        _template: function() {
            return  '<div class="ui-color-picker">' +
                        '<div class="ui-color-picker-header">' +
                            '<div class="ui-color-picker-value"/>' +
                            '<div class="ui-color-picker-label">Select a color</div>' +
                        '</div>' +
                        '<div class="ui-color-picker-view ui-input">' +
                            '<div class="ui-color-picker-panel"/>' +
                        '</div>'
                    '</div>';
        }
    });
});