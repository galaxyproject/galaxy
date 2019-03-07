var Backbone = require("backbone");

var Seqpanel = Backbone.View.extend({
    events: {
        "click #perform": "drawInput"
    },
    initialize: function(opts){
        this.struct = opts.struct;
        this.el = opts.el;
        this.el.className += "container-fluid";
        this.el.id = "seqinput";

        this.listenTo(this.struct, "change:seq", this.updateSeq);
        this.listenTo(this.struct, "change:dotbr", this.updateDotbr);
    },
    render: function(){
        this.el.innerHTML += '<div class="col-md-11 seqin"><input type="text" class="alertfield" id="alert" readonly>'
                        + '<input class="textbox" id="seqbox">'
                        + '<input class="textbox" id="dotbrbox"></div>';
        this.el.innerHTML += '<div class="col-md-1 seqin">'
                        + '<input class="button" id="perform" value="Display" readonly="readonly">'
                        + '</div>';
        document.getElementById("seqbox").value = this.struct.get("seq");
        document.getElementById("dotbrbox").value = this.struct.get("dotbr");
        this.el.style.paddingBottom = "20px";
    },
    updateSeq: function(){
        document.getElementById("seqbox").value = this.struct.get("seq");
    },
    updateDotbr: function(){
        document.getElementById("dotbrbox").value = this.struct.get("dotbr");
    },
    drawInput: function(){
        var sequ = [
            document.getElementById("seqbox").value,
            document.getElementById("dotbrbox").value
        ];
        var state = this.checkInput(sequ);
        if(state.fine){
            this.struct.set("seq", sequ[0]);
            this.struct.set("dotbr", sequ[1]);
            this.struct.set("renderSwitch", !this.struct.get("renderSwitch"));
        }
        else {
            var al = document.getElementById("alert");
            if(al){
                al.value = state.msg;
            }
        }
    },
    checkInput: function(sequences){
        var isFine = true;
        var errMsg = "";

        if(sequences[0].length === 0 || sequences[1].length === 0){
          isFine = false;
          errMsg = "Please enter a sequence!";
        }
        else if(sequences[0].length != sequences[1].length){
          isFine = false;
          errMsg = "Sequences must have equal length!";
        }
        else if(! sequences[1].match('^[().]+$')){
          isFine = false;
          errMsg = "Dot-bracket sequence may only contain \"(\", \")\", or \".\"!";
        }
        else if(! sequences[0].match('^[ACGUTRYSWKMBDHVNacgutryswkmbdhvn-]+$')){
          isFine = false;
          errMsg = "Sequence may only contain IUPAC-characters!";
        }
        return {
            fine: isFine,
            msg: errMsg
        };
    }
});

module.exports = Seqpanel;
