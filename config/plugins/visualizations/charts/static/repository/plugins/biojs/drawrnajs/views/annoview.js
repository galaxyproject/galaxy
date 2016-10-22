var Backbone = require("backbone");
var NCAnno = require("../models/ncanno");
var $ = jQuery = require("jquery");
var bootstrap = require("bootstrap");

var AnnoView = Backbone.View.extend({
    events: {
        "click #annook": "applyAnno",
        "click #wc1": "selectWc1",
        "click #hg1": "selectHg1",
        "click #sg1": "selectSg1",
        "click #wc2": "selectWc2",
        "click #hg2": "selectHg2",
        "click #sg2": "selectSg2",
        "click #st1": "selectStericityCis",
        "click #st2": "selectStericityTrans"
    },
    initialize: function(b1, b2, st, edge, cyEle){
        var el = document.createElement("div");
        cyEle.parentNode.appendChild(el);
        this.setElement(el);
        this.anno = new NCAnno(b1, b2, st, edge);
        //CSS
        this.defineStyle();
        this.render();
    },
    applyAnno: function(){
        var e1 = this.anno.get("base1");
        var e2 = this.anno.get("base2");
        var st = this.anno.get("stericity");
        this.anno.get("edge")._private.classes = {};
        this.anno.get("edge").addClass(e1 + e2 + st);
        this.remove();
    },
    render: function(){
        //HTML SETUP
        var res1 = this.anno.get("edge").source().data("label");
        var res2 = this.anno.get("edge").target().data("label");
        var edefs = this.anno.getLabels();

        this.el.innerHTML += "<div class='col-md-4'>"
            + "<span>Residue: " +  res1 + "</span>"
            + "<div class='dropdown'>"
            + "<button class='btn btn-default dropdown-toggle' type='button' id='menu1' data-toggle='dropdown'>" + edefs[0]
            + "<span class='caret'></span></button>"
            + "<ul class='dropdown-menu' role='menu' aria-labelledby='menu1'>"
            + "<li role='presentation'><span class='text-muted' id='wc1' style='cursor: pointer;'>Watson-Crick</span></li>"
            + "<li role='presentation'><span class='text-muted' id='hg1' style='cursor: pointer;'>Hoogsteen</span></li>"
            + "<li role='presentation'><span class='text-muted' id='sg1' style='cursor: pointer;'>Sugar</span></li>"
            + "</ul>"
            + "</div>"
            + "</div>";
        this.el.innerHTML += "<div class='col-md-4'>"
            + "<span>Residue: " +  res2 + "</span>"
            + "<div class='dropdown'>"
            + "<button class='btn btn-default dropdown-toggle' type='button' id='menu2' data-toggle='dropdown'>" + edefs[1]
            + "<span class='caret'></span></button>"
            + "<ul class='dropdown-menu' role='menu' aria-labelledby='menu2'>"
            + "<li role='presentation'><span class='text-muted' id='wc2' style='cursor: pointer;'>Watson-Crick</span></li>"
            + "<li role='presentation'><span class='text-muted' id='hg2' style='cursor: pointer;'>Hoogsteen</span></li>"
            + "<li role='presentation'><span class='text-muted' id='sg2' style='cursor: pointer;'>Sugar</span></li>"
            + "</ul>"
            + "</div>"
            + "</div>";
        this.el.innerHTML += ""
            + "<div class='col-md-3'><div class='dropdown'>"
            + "<button class='btn btn-default dropdown-toggle' type='button' id='menu3' data-toggle='dropdown' style='margin-top: 19px;'>" + edefs[2]
            + "<span class='caret'></span></button>"
            + "<ul class='dropdown-menu'>"
            + "<li role='presentation'><span class='text-muted' id='st1' style='cursor: pointer;'>cis</span></li>"
            + "<li role='presentation'><span class='text-muted' id='st2' style='cursor: pointer;'>trans</span></li>"
            + "</ul>"
            + "</div></div>";

        this.el.innerHTML += "<div class='col-md-1'><button class='btn btn-default' type='button' id='annook' style='margin-top: 19px;'>OK"
            + "</button></div>";
    },
    defineStyle: function(){
        var st = this.el.style;
        st.display = "block";
        st.position = "absolute";
        st.left = "1%";
        st.width = "435px";
        st.height = "170px";
        st.padding = "10px";
        st.paddingRight = "55px";
        st.border = "1px solid black";
        st.borderRadius = "1px";
        st.backgroundColor = "#F6F6F6";
        st.overflow = "auto";
        st.fontWeight = "bold";
        st.textAlign = "center";
        st.zIndex = 1002;
    },
    selectWc1: function(){
        this.anno.set("base1", "wc");
        document.getElementById("menu1").innerHTML = "Watson-Crick<span class='caret'></span>";
    },
    selectHg1: function(){
        this.anno.set("base1", "hg");
        document.getElementById("menu1").innerHTML = "Hoogsteen<span class='caret'></span>";
    },
    selectSg1: function(){
        this.anno.set("base1", "sg");
        document.getElementById("menu1").innerHTML = "Sugar<span class='caret'></span>";
    },
    selectWc2: function(){
        this.anno.set("base2", "wc");
        document.getElementById("menu2").innerHTML = "Watson-Crick<span class='caret'></span>";
    },
    selectHg2: function(){
        this.anno.set("base2", "hg");
        document.getElementById("menu2").innerHTML = "Hoogsteen<span class='caret'></span>";
    },
    selectSg2: function(){
        this.anno.set("base2", "sg");
        document.getElementById("menu2").innerHTML = "Sugar<span class='caret'></span>";
    },
    selectStericityCis: function(){
        this.anno.set("stericity", "cis");
        document.getElementById("menu3").innerHTML = "Cis<span class='caret'></span>";
    },
    selectStericityTrans: function(){
        this.anno.set("stericity", "trans");
        document.getElementById("menu3").innerHTML = "Trans<span class='caret'></span>";
    }
});

module.exports = AnnoView;
