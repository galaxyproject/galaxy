!function(a){"function"==typeof define&&define.amd?define([],a):a(jQuery)}(function(){function a(a,b){return this.currModeIndex=0,this._init(a,b)}a.prototype.DATA_KEY="mode-button",a.prototype.defaults={switchModesOnClick:!0},a.prototype._init=function(a,b){if(b=b||{},this.$element=$(a),this.options=$.extend(!0,{},this.defaults,b),!b.modes)throw new Error('ModeButton requires a "modes" array');var c=this;return this.$element.click(function(a){c.callModeFn(),c.options.switchModesOnClick&&c._incModeIndex(),$(this).html(c.options.modes[c.currModeIndex].html)}),this.reset()},a.prototype._incModeIndex=function(){return this.currModeIndex+=1,this.currModeIndex>=this.options.modes.length&&(this.currModeIndex=0),this},a.prototype._getModeIndex=function(a){for(var b=0;b<this.options.modes.length;b+=1)if(this.options.modes[b].mode===a)return b;throw new Error("mode not found: "+a)},a.prototype._setModeByIndex=function(a){var b=this.options.modes[a];if(!b)throw new Error("mode index not found: "+a);return this.currModeIndex=a,b.html&&this.$element.html(b.html),this},a.prototype.currentMode=function(){return this.options.modes[this.currModeIndex]},a.prototype.current=function(){return this.currentMode().mode},a.prototype.getMode=function(a){return a?this.options.modes[this._getModeIndex(a)]:this.currentMode()},a.prototype.hasMode=function(a){try{return!!this.getMode(a)}catch(b){}return!1},a.prototype.setMode=function(a){return this._setModeByIndex(this._getModeIndex(a))},a.prototype.reset=function(){return this.currModeIndex=0,this.options.initialMode&&(this.currModeIndex=this._getModeIndex(this.options.initialMode)),this._setModeByIndex(this.currModeIndex)},a.prototype.callModeFn=function(a){var b=this.getMode(a).onclick;if(b&&$.type("function"===b))return b.call(this.$element.get(0))},$.fn.modeButton=function(b){if(!this.length)return this;if("object"===$.type(b))return this.map(function(){var c=$(this);return c.data("mode-button",new a(c,b)),this});var c=$(this[0]),d=c.data("mode-button");if(!d)throw new Error("modeButton needs an options object or string name of a function");if(d&&"string"===$.type(b)){var e=b;if(d&&"function"===$.type(d[e]))return d[e].apply(d,$.makeArray(arguments).slice(1))}return d}});
//# sourceMappingURL=../../maps/ui/mode-button.js.map