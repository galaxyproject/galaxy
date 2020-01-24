var setupLasso = module.exports = function($){
    //Lasso Functionality
    var $ = require( 'jquery' );
    $.fn.extend({
      lasso: function () {
         this.mousedown(function (e) {
            // left mouse down switches on "capturing mode"
            if (e.which === 1 && !$(this).is(".lassoRunning")) {
              $(this).addClass("lassoRunning");
              $(this).data("lassoPoints", []);
              $(this).trigger("lassoBegin");
            }
          });
          this.mouseup(function (e) {
            // left mouse up ends "capturing mode" + triggers "Done" event
            if (e.which === 1 && $(this).is(".lassoRunning")) {
              $(this).removeClass("lassoRunning");
              $(this).trigger("lassoDone", [$(this).data("lassoPoints")]);
            }
          });
          this.mousemove(function (e) {
            // mouse move captures co-ordinates + triggers "Point" event
            if ($(this).is(".lassoRunning")) {
              var px = (e.offsetX || e.clientX - $(e.target).offset().left + window.pageXOffset);
              var py = (e.offsetY || e.clientY - $(e.target).offset().top + window.pageYOffset);
              var point = [px, py];
              $(this).data("lassoPoints").push(point);
              $(this).trigger("lassoPoint", [point]);
            }
          });
          return this;
      }
    });
}
