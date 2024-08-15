if(!document.createElement("canvas").getContext){(function(){var z=Math;var K=z.round;var J=z.sin;var U=z.cos;var b=z.abs;var k=z.sqrt;var D=10;var F=D/2;function T(){return this.context_||(this.context_=new W(this))}var O=Array.prototype.slice;function G(i,j,m){var Z=O.call(arguments,2);return function(){return i.apply(j,Z.concat(O.call(arguments)))}}function AD(Z){return String(Z).replace(/&/g,"&amp;").replace(/"/g,"&quot;")}function r(i){if(!i.namespaces.g_vml_){i.namespaces.add("g_vml_","urn:schemas-microsoft-com:vml","#default#VML")}if(!i.namespaces.g_o_){i.namespaces.add("g_o_","urn:schemas-microsoft-com:office:office","#default#VML")}if(!i.styleSheets.ex_canvas_){var Z=i.createStyleSheet();Z.owningElement.id="ex_canvas_";Z.cssText="canvas{display:inline-block;overflow:hidden;text-align:left;width:300px;height:150px}"}}r(document);var E={init:function(Z){if(/MSIE/.test(navigator.userAgent)&&!window.opera){var i=Z||document;i.createElement("canvas");i.attachEvent("onreadystatechange",G(this.init_,this,i))}},init_:function(m){var j=m.getElementsByTagName("canvas");for(var Z=0;Z<j.length;Z++){this.initElement(j[Z])}},initElement:function(i){if(!i.getContext){i.getContext=T;r(i.ownerDocument);i.innerHTML="";i.attachEvent("onpropertychange",S);i.attachEvent("onresize",w);var Z=i.attributes;if(Z.width&&Z.width.specified){i.style.width=Z.width.nodeValue+"px"}else{i.width=i.clientWidth}if(Z.height&&Z.height.specified){i.style.height=Z.height.nodeValue+"px"}else{i.height=i.clientHeight}}return i}};function S(i){var Z=i.srcElement;switch(i.propertyName){case"width":Z.getContext().clearRect();Z.style.width=Z.attributes.width.nodeValue+"px";Z.firstChild.style.width=Z.clientWidth+"px";break;case"height":Z.getContext().clearRect();Z.style.height=Z.attributes.height.nodeValue+"px";Z.firstChild.style.height=Z.clientHeight+"px";break}}function w(i){var Z=i.srcElement;if(Z.firstChild){Z.firstChild.style.width=Z.clientWidth+"px";Z.firstChild.style.height=Z.clientHeight+"px"}}E.init();var I=[];for(var AC=0;AC<16;AC++){for(var AB=0;AB<16;AB++){I[AC*16+AB]=AC.toString(16)+AB.toString(16)}}function V(){return[[1,0,0],[0,1,0],[0,0,1]]}function d(m,j){var i=V();for(var Z=0;Z<3;Z++){for(var AF=0;AF<3;AF++){var p=0;for(var AE=0;AE<3;AE++){p+=m[Z][AE]*j[AE][AF]}i[Z][AF]=p}}return i}function Q(i,Z){Z.fillStyle=i.fillStyle;Z.lineCap=i.lineCap;Z.lineJoin=i.lineJoin;Z.lineWidth=i.lineWidth;Z.miterLimit=i.miterLimit;Z.shadowBlur=i.shadowBlur;Z.shadowColor=i.shadowColor;Z.shadowOffsetX=i.shadowOffsetX;Z.shadowOffsetY=i.shadowOffsetY;Z.strokeStyle=i.strokeStyle;Z.globalAlpha=i.globalAlpha;Z.font=i.font;Z.textAlign=i.textAlign;Z.textBaseline=i.textBaseline;Z.arcScaleX_=i.arcScaleX_;Z.arcScaleY_=i.arcScaleY_;Z.lineScale_=i.lineScale_}var B={aliceblue:"#F0F8FF",antiquewhite:"#FAEBD7",aquamarine:"#7FFFD4",azure:"#F0FFFF",beige:"#F5F5DC",bisque:"#FFE4C4",black:"#000000",blanchedalmond:"#FFEBCD",blueviolet:"#8A2BE2",brown:"#A52A2A",burlywood:"#DEB887",cadetblue:"#5F9EA0",chartreuse:"#7FFF00",chocolate:"#D2691E",coral:"#FF7F50",cornflowerblue:"#6495ED",cornsilk:"#FFF8DC",crimson:"#DC143C",cyan:"#00FFFF",darkblue:"#00008B",darkcyan:"#008B8B",darkgoldenrod:"#B8860B",darkgray:"#A9A9A9",darkgreen:"#006400",darkgrey:"#A9A9A9",darkkhaki:"#BDB76B",darkmagenta:"#8B008B",darkolivegreen:"#556B2F",darkorange:"#FF8C00",darkorchid:"#9932CC",darkred:"#8B0000",darksalmon:"#E9967A",darkseagreen:"#8FBC8F",darkslateblue:"#483D8B",darkslategray:"#2F4F4F",darkslategrey:"#2F4F4F",darkturquoise:"#00CED1",darkviolet:"#9400D3",deeppink:"#FF1493",deepskyblue:"#00BFFF",dimgray:"#696969",dimgrey:"#696969",dodgerblue:"#1E90FF",firebrick:"#B22222",floralwhite:"#FFFAF0",forestgreen:"#228B22",gainsboro:"#DCDCDC",ghostwhite:"#F8F8FF",gold:"#FFD700",goldenrod:"#DAA520",grey:"#808080",greenyellow:"#ADFF2F",honeydew:"#F0FFF0",hotpink:"#FF69B4",indianred:"#CD5C5C",indigo:"#4B0082",ivory:"#FFFFF0",khaki:"#F0E68C",lavender:"#E6E6FA",lavenderblush:"#FFF0F5",lawngreen:"#7CFC00",lemonchiffon:"#FFFACD",lightblue:"#ADD8E6",lightcoral:"#F08080",lightcyan:"#E0FFFF",lightgoldenrodyellow:"#FAFAD2",lightgreen:"#90EE90",lightgrey:"#D3D3D3",lightpink:"#FFB6C1",lightsalmon:"#FFA07A",lightseagreen:"#20B2AA",lightskyblue:"#87CEFA",lightslategray:"#778899",lightslategrey:"#778899",lightsteelblue:"#B0C4DE",lightyellow:"#FFFFE0",limegreen:"#32CD32",linen:"#FAF0E6",magenta:"#FF00FF",mediumaquamarine:"#66CDAA",mediumblue:"#0000CD",mediumorchid:"#BA55D3",mediumpurple:"#9370DB",mediumseagreen:"#3CB371",mediumslateblue:"#7B68EE",mediumspringgreen:"#00FA9A",mediumturquoise:"#48D1CC",mediumvioletred:"#C71585",midnightblue:"#191970",mintcream:"#F5FFFA",mistyrose:"#FFE4E1",moccasin:"#FFE4B5",navajowhite:"#FFDEAD",oldlace:"#FDF5E6",olivedrab:"#6B8E23",orange:"#FFA500",orangered:"#FF4500",orchid:"#DA70D6",palegoldenrod:"#EEE8AA",palegreen:"#98FB98",paleturquoise:"#AFEEEE",palevioletred:"#DB7093",papayawhip:"#FFEFD5",peachpuff:"#FFDAB9",peru:"#CD853F",pink:"#FFC0CB",plum:"#DDA0DD",powderblue:"#B0E0E6",rosybrown:"#BC8F8F",royalblue:"#4169E1",saddlebrown:"#8B4513",salmon:"#FA8072",sandybrown:"#F4A460",seagreen:"#2E8B57",seashell:"#FFF5EE",sienna:"#A0522D",skyblue:"#87CEEB",slateblue:"#6A5ACD",slategray:"#708090",slategrey:"#708090",snow:"#FFFAFA",springgreen:"#00FF7F",steelblue:"#4682B4",tan:"#D2B48C",thistle:"#D8BFD8",tomato:"#FF6347",turquoise:"#40E0D0",violet:"#EE82EE",wheat:"#F5DEB3",whitesmoke:"#F5F5F5",yellowgreen:"#9ACD32"};function g(i){var m=i.indexOf("(",3);var Z=i.indexOf(")",m+1);var j=i.substring(m+1,Z).split(",");if(j.length==4&&i.substr(3,1)=="a"){alpha=Number(j[3])}else{j[3]=1}return j}function C(Z){return parseFloat(Z)/100}function N(i,j,Z){return Math.min(Z,Math.max(j,i))}function c(AF){var j,i,Z;h=parseFloat(AF[0])/360%360;if(h<0){h++}s=N(C(AF[1]),0,1);l=N(C(AF[2]),0,1);if(s==0){j=i=Z=l}else{var m=l<0.5?l*(1+s):l+s-l*s;var AE=2*l-m;j=A(AE,m,h+1/3);i=A(AE,m,h);Z=A(AE,m,h-1/3)}return"#"+I[Math.floor(j*255)]+I[Math.floor(i*255)]+I[Math.floor(Z*255)]}function A(i,Z,j){if(j<0){j++}if(j>1){j--}if(6*j<1){return i+(Z-i)*6*j}else{if(2*j<1){return Z}else{if(3*j<2){return i+(Z-i)*(2/3-j)*6}else{return i}}}}function Y(Z){var AE,p=1;Z=String(Z);if(Z.charAt(0)=="#"){AE=Z}else{if(/^rgb/.test(Z)){var m=g(Z);var AE="#",AF;for(var j=0;j<3;j++){if(m[j].indexOf("%")!=-1){AF=Math.floor(C(m[j])*255)}else{AF=Number(m[j])}AE+=I[N(AF,0,255)]}p=m[3]}else{if(/^hsl/.test(Z)){var m=g(Z);AE=c(m);p=m[3]}else{AE=B[Z]||Z}}}return{color:AE,alpha:p}}var L={style:"normal",variant:"normal",weight:"normal",size:10,family:"sans-serif"};var f={};function X(Z){if(f[Z]){return f[Z]}var m=document.createElement("div");var j=m.style;try{j.font=Z}catch(i){}return f[Z]={style:j.fontStyle||L.style,variant:j.fontVariant||L.variant,weight:j.fontWeight||L.weight,size:j.fontSize||L.size,family:j.fontFamily||L.family}}function P(j,i){var Z={};for(var AF in j){Z[AF]=j[AF]}var AE=parseFloat(i.currentStyle.fontSize),m=parseFloat(j.size);if(typeof j.size=="number"){Z.size=j.size}else{if(j.size.indexOf("px")!=-1){Z.size=m}else{if(j.size.indexOf("em")!=-1){Z.size=AE*m}else{if(j.size.indexOf("%")!=-1){Z.size=(AE/100)*m}else{if(j.size.indexOf("pt")!=-1){Z.size=m/0.75}else{Z.size=AE}}}}}Z.size*=0.981;return Z}function AA(Z){return Z.style+" "+Z.variant+" "+Z.weight+" "+Z.size+"px "+Z.family}function t(Z){switch(Z){case"butt":return"flat";case"round":return"round";case"square":default:return"square"}}function W(i){this.m_=V();this.mStack_=[];this.aStack_=[];this.currentPath_=[];this.strokeStyle="#000";this.fillStyle="#000";this.lineWidth=1;this.lineJoin="miter";this.lineCap="butt";this.miterLimit=D*1;this.globalAlpha=1;this.font="10px sans-serif";this.textAlign="left";this.textBaseline="alphabetic";this.canvas=i;var Z=i.ownerDocument.createElement("div");Z.style.width=i.clientWidth+"px";Z.style.height=i.clientHeight+"px";Z.style.overflow="hidden";Z.style.position="absolute";i.appendChild(Z);this.element_=Z;this.arcScaleX_=1;this.arcScaleY_=1;this.lineScale_=1}var M=W.prototype;M.clearRect=function(){if(this.textMeasureEl_){this.textMeasureEl_.removeNode(true);this.textMeasureEl_=null}this.element_.innerHTML=""};M.beginPath=function(){this.currentPath_=[]};M.moveTo=function(i,Z){var j=this.getCoords_(i,Z);this.currentPath_.push({type:"moveTo",x:j.x,y:j.y});this.currentX_=j.x;this.currentY_=j.y};M.lineTo=function(i,Z){var j=this.getCoords_(i,Z);this.currentPath_.push({type:"lineTo",x:j.x,y:j.y});this.currentX_=j.x;this.currentY_=j.y};M.bezierCurveTo=function(j,i,AI,AH,AG,AE){var Z=this.getCoords_(AG,AE);var AF=this.getCoords_(j,i);var m=this.getCoords_(AI,AH);e(this,AF,m,Z)};function e(Z,m,j,i){Z.currentPath_.push({type:"bezierCurveTo",cp1x:m.x,cp1y:m.y,cp2x:j.x,cp2y:j.y,x:i.x,y:i.y});Z.currentX_=i.x;Z.currentY_=i.y}M.quadraticCurveTo=function(AG,j,i,Z){var AF=this.getCoords_(AG,j);var AE=this.getCoords_(i,Z);var AH={x:this.currentX_+2/3*(AF.x-this.currentX_),y:this.currentY_+2/3*(AF.y-this.currentY_)};var m={x:AH.x+(AE.x-this.currentX_)/3,y:AH.y+(AE.y-this.currentY_)/3};e(this,AH,m,AE)};M.arc=function(AJ,AH,AI,AE,i,j){AI*=D;var AN=j?"at":"wa";var AK=AJ+U(AE)*AI-F;var AM=AH+J(AE)*AI-F;var Z=AJ+U(i)*AI-F;var AL=AH+J(i)*AI-F;if(AK==Z&&!j){AK+=0.125}var m=this.getCoords_(AJ,AH);var AG=this.getCoords_(AK,AM);var AF=this.getCoords_(Z,AL);this.currentPath_.push({type:AN,x:m.x,y:m.y,radius:AI,xStart:AG.x,yStart:AG.y,xEnd:AF.x,yEnd:AF.y})};M.rect=function(j,i,Z,m){this.moveTo(j,i);this.lineTo(j+Z,i);this.lineTo(j+Z,i+m);this.lineTo(j,i+m);this.closePath()};M.strokeRect=function(j,i,Z,m){var p=this.currentPath_;this.beginPath();this.moveTo(j,i);this.lineTo(j+Z,i);this.lineTo(j+Z,i+m);this.lineTo(j,i+m);this.closePath();this.stroke();this.currentPath_=p};M.fillRect=function(j,i,Z,m){var p=this.currentPath_;this.beginPath();this.moveTo(j,i);this.lineTo(j+Z,i);this.lineTo(j+Z,i+m);this.lineTo(j,i+m);this.closePath();this.fill();this.currentPath_=p};M.createLinearGradient=function(i,m,Z,j){var p=new v("gradient");p.x0_=i;p.y0_=m;p.x1_=Z;p.y1_=j;return p};M.createRadialGradient=function(m,AE,j,i,p,Z){var AF=new v("gradientradial");AF.x0_=m;AF.y0_=AE;AF.r0_=j;AF.x1_=i;AF.y1_=p;AF.r1_=Z;return AF};M.drawImage=function(AO,j){var AH,AF,AJ,AV,AM,AK,AQ,AX;var AI=AO.runtimeStyle.width;var AN=AO.runtimeStyle.height;AO.runtimeStyle.width="auto";AO.runtimeStyle.height="auto";var AG=AO.width;var AT=AO.height;AO.runtimeStyle.width=AI;AO.runtimeStyle.height=AN;if(arguments.length==3){AH=arguments[1];AF=arguments[2];AM=AK=0;AQ=AJ=AG;AX=AV=AT}else{if(arguments.length==5){AH=arguments[1];AF=arguments[2];AJ=arguments[3];AV=arguments[4];AM=AK=0;AQ=AG;AX=AT}else{if(arguments.length==9){AM=arguments[1];AK=arguments[2];AQ=arguments[3];AX=arguments[4];AH=arguments[5];AF=arguments[6];AJ=arguments[7];AV=arguments[8]}else{throw Error("Invalid number of arguments")}}}var AW=this.getCoords_(AH,AF);var m=AQ/2;var i=AX/2;var AU=[];var Z=10;var AE=10;AU.push(" <g_vml_:group",' coordsize="',D*Z,",",D*AE,'"',' coordorigin="0,0"',' style="width:',Z,"px;height:",AE,"px;position:absolute;");if(this.m_[0][0]!=1||this.m_[0][1]||this.m_[1][1]!=1||this.m_[1][0]){var p=[];p.push("M11=",this.m_[0][0],",","M12=",this.m_[1][0],",","M21=",this.m_[0][1],",","M22=",this.m_[1][1],",","Dx=",K(AW.x/D),",","Dy=",K(AW.y/D),"");var AS=AW;var AR=this.getCoords_(AH+AJ,AF);var AP=this.getCoords_(AH,AF+AV);var AL=this.getCoords_(AH+AJ,AF+AV);AS.x=z.max(AS.x,AR.x,AP.x,AL.x);AS.y=z.max(AS.y,AR.y,AP.y,AL.y);AU.push("padding:0 ",K(AS.x/D),"px ",K(AS.y/D),"px 0;filter:progid:DXImageTransform.Microsoft.Matrix(",p.join(""),", sizingmethod='clip');")}else{AU.push("top:",K(AW.y/D),"px;left:",K(AW.x/D),"px;")}AU.push(' ">','<g_vml_:image src="',AO.src,'"',' style="width:',D*AJ,"px;"," height:",D*AV,'px"',' cropleft="',AM/AG,'"',' croptop="',AK/AT,'"',' cropright="',(AG-AM-AQ)/AG,'"',' cropbottom="',(AT-AK-AX)/AT,'"'," />","</g_vml_:group>");this.element_.insertAdjacentHTML("BeforeEnd",AU.join(""))};M.stroke=function(AM){var m=10;var AN=10;var AE=5000;var AG={x:null,y:null};var AL={x:null,y:null};for(var AH=0;AH<this.currentPath_.length;AH+=AE){var AK=[];var AF=false;AK.push("<g_vml_:shape",' filled="',!!AM,'"',' style="position:absolute;width:',m,"px;height:",AN,'px;"',' coordorigin="0,0"',' coordsize="',D*m,",",D*AN,'"',' stroked="',!AM,'"',' path="');var AO=false;for(var AI=AH;AI<Math.min(AH+AE,this.currentPath_.length);AI++){if(AI%AE==0&&AI>0){AK.push(" m ",K(this.currentPath_[AI-1].x),",",K(this.currentPath_[AI-1].y))}var Z=this.currentPath_[AI];var AJ;switch(Z.type){case"moveTo":AJ=Z;AK.push(" m ",K(Z.x),",",K(Z.y));break;case"lineTo":AK.push(" l ",K(Z.x),",",K(Z.y));break;case"close":AK.push(" x ");Z=null;break;case"bezierCurveTo":AK.push(" c ",K(Z.cp1x),",",K(Z.cp1y),",",K(Z.cp2x),",",K(Z.cp2y),",",K(Z.x),",",K(Z.y));break;case"at":case"wa":AK.push(" ",Z.type," ",K(Z.x-this.arcScaleX_*Z.radius),",",K(Z.y-this.arcScaleY_*Z.radius)," ",K(Z.x+this.arcScaleX_*Z.radius),",",K(Z.y+this.arcScaleY_*Z.radius)," ",K(Z.xStart),",",K(Z.yStart)," ",K(Z.xEnd),",",K(Z.yEnd));break}if(Z){if(AG.x==null||Z.x<AG.x){AG.x=Z.x}if(AL.x==null||Z.x>AL.x){AL.x=Z.x}if(AG.y==null||Z.y<AG.y){AG.y=Z.y}if(AL.y==null||Z.y>AL.y){AL.y=Z.y}}}AK.push(' ">');if(!AM){R(this,AK)}else{a(this,AK,AG,AL)}AK.push("</g_vml_:shape>");this.element_.insertAdjacentHTML("beforeEnd",AK.join(""))}};function R(j,AE){var i=Y(j.strokeStyle);var m=i.color;var p=i.alpha*j.globalAlpha;var Z=j.lineScale_*j.lineWidth;if(Z<1){p*=Z}AE.push("<g_vml_:stroke",' opacity="',p,'"',' joinstyle="',j.lineJoin,'"',' miterlimit="',j.miterLimit,'"',' endcap="',t(j.lineCap),'"',' weight="',Z,'px"',' color="',m,'" />')}function a(AO,AG,Ah,AP){var AH=AO.fillStyle;var AY=AO.arcScaleX_;var AX=AO.arcScaleY_;var Z=AP.x-Ah.x;var m=AP.y-Ah.y;if(AH instanceof v){var AL=0;var Ac={x:0,y:0};var AU=0;var AK=1;if(AH.type_=="gradient"){var AJ=AH.x0_/AY;var j=AH.y0_/AX;var AI=AH.x1_/AY;var Aj=AH.y1_/AX;var Ag=AO.getCoords_(AJ,j);var Af=AO.getCoords_(AI,Aj);var AE=Af.x-Ag.x;var p=Af.y-Ag.y;AL=Math.atan2(AE,p)*180/Math.PI;if(AL<0){AL+=360}if(AL<0.000001){AL=0}}else{var Ag=AO.getCoords_(AH.x0_,AH.y0_);Ac={x:(Ag.x-Ah.x)/Z,y:(Ag.y-Ah.y)/m};Z/=AY*D;m/=AX*D;var Aa=z.max(Z,m);AU=2*AH.r0_/Aa;AK=2*AH.r1_/Aa-AU}var AS=AH.colors_;AS.sort(function(Ak,i){return Ak.offset-i.offset});var AN=AS.length;var AR=AS[0].color;var AQ=AS[AN-1].color;var AW=AS[0].alpha*AO.globalAlpha;var AV=AS[AN-1].alpha*AO.globalAlpha;var Ab=[];for(var Ae=0;Ae<AN;Ae++){var AM=AS[Ae];Ab.push(AM.offset*AK+AU+" "+AM.color)}AG.push('<g_vml_:fill type="',AH.type_,'"',' method="none" focus="100%"',' color="',AR,'"',' color2="',AQ,'"',' colors="',Ab.join(","),'"',' opacity="',AV,'"',' g_o_:opacity2="',AW,'"',' angle="',AL,'"',' focusposition="',Ac.x,",",Ac.y,'" />')}else{if(AH instanceof u){if(Z&&m){var AF=-Ah.x;var AZ=-Ah.y;AG.push("<g_vml_:fill",' position="',AF/Z*AY*AY,",",AZ/m*AX*AX,'"',' type="tile"',' src="',AH.src_,'" />')}}else{var Ai=Y(AO.fillStyle);var AT=Ai.color;var Ad=Ai.alpha*AO.globalAlpha;AG.push('<g_vml_:fill color="',AT,'" opacity="',Ad,'" />')}}}M.fill=function(){this.stroke(true)};M.closePath=function(){this.currentPath_.push({type:"close"})};M.getCoords_=function(j,i){var Z=this.m_;return{x:D*(j*Z[0][0]+i*Z[1][0]+Z[2][0])-F,y:D*(j*Z[0][1]+i*Z[1][1]+Z[2][1])-F}};M.save=function(){var Z={};Q(this,Z);this.aStack_.push(Z);this.mStack_.push(this.m_);this.m_=d(V(),this.m_)};M.restore=function(){if(this.aStack_.length){Q(this.aStack_.pop(),this);this.m_=this.mStack_.pop()}};function H(Z){return isFinite(Z[0][0])&&isFinite(Z[0][1])&&isFinite(Z[1][0])&&isFinite(Z[1][1])&&isFinite(Z[2][0])&&isFinite(Z[2][1])}function y(i,Z,j){if(!H(Z)){return }i.m_=Z;if(j){var p=Z[0][0]*Z[1][1]-Z[0][1]*Z[1][0];i.lineScale_=k(b(p))}}M.translate=function(j,i){var Z=[[1,0,0],[0,1,0],[j,i,1]];y(this,d(Z,this.m_),false)};M.rotate=function(i){var m=U(i);var j=J(i);var Z=[[m,j,0],[-j,m,0],[0,0,1]];y(this,d(Z,this.m_),false)};M.scale=function(j,i){this.arcScaleX_*=j;this.arcScaleY_*=i;var Z=[[j,0,0],[0,i,0],[0,0,1]];y(this,d(Z,this.m_),true)};M.transform=function(p,m,AF,AE,i,Z){var j=[[p,m,0],[AF,AE,0],[i,Z,1]];y(this,d(j,this.m_),true)};M.setTransform=function(AE,p,AG,AF,j,i){var Z=[[AE,p,0],[AG,AF,0],[j,i,1]];y(this,Z,true)};M.drawText_=function(AK,AI,AH,AN,AG){var AM=this.m_,AQ=1000,i=0,AP=AQ,AF={x:0,y:0},AE=[];var Z=P(X(this.font),this.element_);var j=AA(Z);var AR=this.element_.currentStyle;var p=this.textAlign.toLowerCase();switch(p){case"left":case"center":case"right":break;case"end":p=AR.direction=="ltr"?"right":"left";break;case"start":p=AR.direction=="rtl"?"right":"left";break;default:p="left"}switch(this.textBaseline){case"hanging":case"top":AF.y=Z.size/1.75;break;case"middle":break;default:case null:case"alphabetic":case"ideographic":case"bottom":AF.y=-Z.size/2.25;break}switch(p){case"right":i=AQ;AP=0.05;break;case"center":i=AP=AQ/2;break}var AO=this.getCoords_(AI+AF.x,AH+AF.y);AE.push('<g_vml_:line from="',-i,' 0" to="',AP,' 0.05" ',' coordsize="100 100" coordorigin="0 0"',' filled="',!AG,'" stroked="',!!AG,'" style="position:absolute;width:1px;height:1px;">');if(AG){R(this,AE)}else{a(this,AE,{x:-i,y:0},{x:AP,y:Z.size})}var AL=AM[0][0].toFixed(3)+","+AM[1][0].toFixed(3)+","+AM[0][1].toFixed(3)+","+AM[1][1].toFixed(3)+",0,0";var AJ=K(AO.x/D)+","+K(AO.y/D);AE.push('<g_vml_:skew on="t" matrix="',AL,'" ',' offset="',AJ,'" origin="',i,' 0" />','<g_vml_:path textpathok="true" />','<g_vml_:textpath on="true" string="',AD(AK),'" style="v-text-align:',p,";font:",AD(j),'" /></g_vml_:line>');this.element_.insertAdjacentHTML("beforeEnd",AE.join(""))};M.fillText=function(j,Z,m,i){this.drawText_(j,Z,m,i,false)};M.strokeText=function(j,Z,m,i){this.drawText_(j,Z,m,i,true)};M.measureText=function(j){if(!this.textMeasureEl_){var Z='<span style="position:absolute;top:-20000px;left:0;padding:0;margin:0;border:none;white-space:pre;"></span>';this.element_.insertAdjacentHTML("beforeEnd",Z);this.textMeasureEl_=this.element_.lastChild}var i=this.element_.ownerDocument;this.textMeasureEl_.innerHTML="";this.textMeasureEl_.style.font=this.font;this.textMeasureEl_.appendChild(i.createTextNode(j));return{width:this.textMeasureEl_.offsetWidth}};M.clip=function(){};M.arcTo=function(){};M.createPattern=function(i,Z){return new u(i,Z)};function v(Z){this.type_=Z;this.x0_=0;this.y0_=0;this.r0_=0;this.x1_=0;this.y1_=0;this.r1_=0;this.colors_=[]}v.prototype.addColorStop=function(i,Z){Z=Y(Z);this.colors_.push({offset:i,color:Z.color,alpha:Z.alpha})};function u(i,Z){q(i);switch(Z){case"repeat":case null:case"":this.repetition_="repeat";break;case"repeat-x":case"repeat-y":case"no-repeat":this.repetition_=Z;break;default:n("SYNTAX_ERR")}this.src_=i.src;this.width_=i.width;this.height_=i.height}function n(Z){throw new o(Z)}function q(Z){if(!Z||Z.nodeType!=1||Z.tagName!="IMG"){n("TYPE_MISMATCH_ERR")}if(Z.readyState!="complete"){n("INVALID_STATE_ERR")}}function o(Z){this.code=this[Z];this.message=Z+": DOM Exception "+this.code}var x=o.prototype=new Error;x.INDEX_SIZE_ERR=1;x.DOMSTRING_SIZE_ERR=2;x.HIERARCHY_REQUEST_ERR=3;x.WRONG_DOCUMENT_ERR=4;x.INVALID_CHARACTER_ERR=5;x.NO_DATA_ALLOWED_ERR=6;x.NO_MODIFICATION_ALLOWED_ERR=7;x.NOT_FOUND_ERR=8;x.NOT_SUPPORTED_ERR=9;x.INUSE_ATTRIBUTE_ERR=10;x.INVALID_STATE_ERR=11;x.SYNTAX_ERR=12;x.INVALID_MODIFICATION_ERR=13;x.NAMESPACE_ERR=14;x.INVALID_ACCESS_ERR=15;x.VALIDATION_ERR=16;x.TYPE_MISMATCH_ERR=17;G_vmlCanvasManager=E;CanvasRenderingContext2D=W;CanvasGradient=v;CanvasPattern=u;DOMException=o})()};// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

/* Javascript plotting library for jQuery, v. 0.6.
 *
 * Released under the MIT license by IOLA, December 2007.
 *
 */

// first an inline dependency, jquery.colorhelpers.js, we inline it here
// for convenience

/* Plugin for jQuery for working with colors.
 * 
 * Version 1.0.
 * 
 * Inspiration from jQuery color animation plugin by John Resig.
 *
 * Released under the MIT license by Ole Laursen, October 2009.
 *
 * Examples:
 *
 *   $.color.parse("#fff").scale('rgb', 0.25).add('a', -0.5).toString()
 *   var c = $.color.extract($("#mydiv"), 'background-color');
 *   console.log(c.r, c.g, c.b, c.a);
 *   $.color.make(100, 50, 25, 0.4).toString() // returns "rgba(100,50,25,0.4)"
 *
 * Note that .scale() and .add() work in-place instead of returning
 * new objects.
 */ 
(function(){jQuery.color={};jQuery.color.make=function(E,D,B,C){var F={};F.r=E||0;F.g=D||0;F.b=B||0;F.a=C!=null?C:1;F.add=function(I,H){for(var G=0;G<I.length;++G){F[I.charAt(G)]+=H}return F.normalize()};F.scale=function(I,H){for(var G=0;G<I.length;++G){F[I.charAt(G)]*=H}return F.normalize()};F.toString=function(){if(F.a>=1){return"rgb("+[F.r,F.g,F.b].join(",")+")"}else{return"rgba("+[F.r,F.g,F.b,F.a].join(",")+")"}};F.normalize=function(){function G(I,J,H){return J<I?I:(J>H?H:J)}F.r=G(0,parseInt(F.r),255);F.g=G(0,parseInt(F.g),255);F.b=G(0,parseInt(F.b),255);F.a=G(0,F.a,1);return F};F.clone=function(){return jQuery.color.make(F.r,F.b,F.g,F.a)};return F.normalize()};jQuery.color.extract=function(C,B){var D;do{D=C.css(B).toLowerCase();if(D!=""&&D!="transparent"){break}C=C.parent()}while(!jQuery.nodeName(C.get(0),"body"));if(D=="rgba(0, 0, 0, 0)"){D="transparent"}return jQuery.color.parse(D)};jQuery.color.parse=function(E){var D,B=jQuery.color.make;if(D=/rgb\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*\)/.exec(E)){return B(parseInt(D[1],10),parseInt(D[2],10),parseInt(D[3],10))}if(D=/rgba\(\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]{1,3})\s*,\s*([0-9]+(?:\.[0-9]+)?)\s*\)/.exec(E)){return B(parseInt(D[1],10),parseInt(D[2],10),parseInt(D[3],10),parseFloat(D[4]))}if(D=/rgb\(\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*\)/.exec(E)){return B(parseFloat(D[1])*2.55,parseFloat(D[2])*2.55,parseFloat(D[3])*2.55)}if(D=/rgba\(\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\%\s*,\s*([0-9]+(?:\.[0-9]+)?)\s*\)/.exec(E)){return B(parseFloat(D[1])*2.55,parseFloat(D[2])*2.55,parseFloat(D[3])*2.55,parseFloat(D[4]))}if(D=/#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})/.exec(E)){return B(parseInt(D[1],16),parseInt(D[2],16),parseInt(D[3],16))}if(D=/#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])/.exec(E)){return B(parseInt(D[1]+D[1],16),parseInt(D[2]+D[2],16),parseInt(D[3]+D[3],16))}var C=jQuery.trim(E).toLowerCase();if(C=="transparent"){return B(255,255,255,0)}else{D=A[C];return B(D[0],D[1],D[2])}};var A={aqua:[0,255,255],azure:[240,255,255],beige:[245,245,220],black:[0,0,0],blue:[0,0,255],brown:[165,42,42],cyan:[0,255,255],darkblue:[0,0,139],darkcyan:[0,139,139],darkgrey:[169,169,169],darkgreen:[0,100,0],darkkhaki:[189,183,107],darkmagenta:[139,0,139],darkolivegreen:[85,107,47],darkorange:[255,140,0],darkorchid:[153,50,204],darkred:[139,0,0],darksalmon:[233,150,122],darkviolet:[148,0,211],fuchsia:[255,0,255],gold:[255,215,0],green:[0,128,0],indigo:[75,0,130],khaki:[240,230,140],lightblue:[173,216,230],lightcyan:[224,255,255],lightgreen:[144,238,144],lightgrey:[211,211,211],lightpink:[255,182,193],lightyellow:[255,255,224],lime:[0,255,0],magenta:[255,0,255],maroon:[128,0,0],navy:[0,0,128],olive:[128,128,0],orange:[255,165,0],pink:[255,192,203],purple:[128,0,128],violet:[128,0,128],red:[255,0,0],silver:[192,192,192],white:[255,255,255],yellow:[255,255,0]}})();

// the actual Flot code
(function($) {
    function Plot(placeholder, data_, options_, plugins) {
        // data is on the form:
        //   [ series1, series2 ... ]
        // where series is either just the data as [ [x1, y1], [x2, y2], ... ]
        // or { data: [ [x1, y1], [x2, y2], ... ], label: "some label", ... }
        
        var series = [],
            options = {
                // the color theme used for graphs
                colors: ["#edc240", "#afd8f8", "#cb4b4b", "#4da74d", "#9440ed"],
                legend: {
                    show: true,
                    noColumns: 1, // number of colums in legend table
                    labelFormatter: null, // fn: string -> string
                    labelBoxBorderColor: "#ccc", // border color for the little label boxes
                    container: null, // container (as jQuery object) to put legend in, null means default on top of graph
                    position: "ne", // position of default legend container within plot
                    margin: 5, // distance from grid edge to default legend container within plot
                    backgroundColor: null, // null means auto-detect
                    backgroundOpacity: 0.85 // set to 0 to avoid background
                },
                xaxis: {
                    position: "bottom", // or "top"
                    mode: null, // null or "time"
                    color: null, // base color, labels, ticks
                    tickColor: null, // possibly different color of ticks, e.g. "rgba(0,0,0,0.15)"
                    transform: null, // null or f: number -> number to transform axis
                    inverseTransform: null, // if transform is set, this should be the inverse function
                    min: null, // min. value to show, null means set automatically
                    max: null, // max. value to show, null means set automatically
                    autoscaleMargin: null, // margin in % to add if auto-setting min/max
                    ticks: null, // either [1, 3] or [[1, "a"], 3] or (fn: axis info -> ticks) or app. number of ticks for auto-ticks
                    tickFormatter: null, // fn: number -> string
                    labelWidth: null, // size of tick labels in pixels
                    labelHeight: null,
                    tickLength: null, // size in pixels of ticks, or "full" for whole line
                    alignTicksWithAxis: null, // axis number or null for no sync
                    
                    // mode specific options
                    tickDecimals: null, // no. of decimals, null means auto
                    tickSize: null, // number or [number, "unit"]
                    minTickSize: null, // number or [number, "unit"]
                    monthNames: null, // list of names of months
                    timeformat: null, // format string to use
                    twelveHourClock: false // 12 or 24 time in time mode
                },
                yaxis: {
                    autoscaleMargin: 0.02,
                    position: "left" // or "right"
                },
                xaxes: [],
                yaxes: [],
                series: {
                    points: {
                        show: false,
                        radius: 3,
                        lineWidth: 2, // in pixels
                        fill: true,
                        fillColor: "#ffffff",
                        symbol: "circle" // or callback
                    },
                    lines: {
                        // we don't put in show: false so we can see
                        // whether lines were actively disabled 
                        lineWidth: 2, // in pixels
                        fill: false,
                        fillColor: null,
                        steps: false
                    },
                    peaks: {
                        lineWidth: 1, // in pixels
                        print: false
                    },
                    bars: {
                        show: false,
                        lineWidth: 2, // in pixels
                        barWidth: 1, // in units of the x axis
                        fill: true,
                        fillColor: null,
                        align: "left", // or "center" 
                        horizontal: false
                    },
                    shadowSize: 3
                },
                grid: {
                    show: true,
                    aboveData: false,
                    color: "#545454", // primary color used for outline and labels
                    backgroundColor: null, // null for transparent, else color
                    borderColor: null, // set if different from the grid color
                    tickColor: null, // color for the ticks, e.g. "rgba(0,0,0,0.15)"
                    labelMargin: 5, // in pixels
                    axisMargin: 8, // in pixels
                    borderWidth: 2, // in pixels
                    markings: null, // array of ranges or fn: axes -> array of ranges
                    markingsColor: "#f4f4f4",
                    markingsLineWidth: 2,
                    // interactive stuff
                    clickable: false,
                    hoverable: false,
                    autoHighlight: true, // highlight in case mouse is near
                    mouseActiveRadius: 10 // how far the mouse can be away to activate an item
                },
                hooks: {}
            },
        canvas = null,      // the canvas for the plot itself
        overlay = null,     // canvas for interactive stuff on top of plot
        eventHolder = null, // jQuery object that events should be bound to
        ctx = null, octx = null,
        xaxes = [], yaxes = [],
        plotOffset = { left: 0, right: 0, top: 0, bottom: 0},
        canvasWidth = 0, canvasHeight = 0,
        plotWidth = 0, plotHeight = 0,
        hooks = {
            processOptions: [],
            processRawData: [],
            processDatapoints: [],
            drawSeries: [],
            draw: [],
            bindEvents: [],
            drawOverlay: []
        },
        plot = this;

        // public functions
        plot.setData = setData;
        plot.setupGrid = setupGrid;
        plot.draw = draw;
        plot.getPlaceholder = function() { return placeholder; };
        plot.getCanvas = function() { return canvas; };
        plot.getPlotOffset = function() { return plotOffset; };
        plot.width = function () { return plotWidth; };
        plot.height = function () { return plotHeight; };
        plot.offset = function () {
            var o = eventHolder.offset();
            o.left += plotOffset.left;
            o.top += plotOffset.top;
            return o;
        };
        plot.getData = function () { return series; };
        plot.getAxis = function (dir, number) {
            var a = (dir == x ? xaxes : yaxes)[number - 1];
            if (a && !a.used)
                a = null;
            return a;
        };
        plot.getAxes = function () {
            var res = {}, i;
            for (i = 0; i < xaxes.length; ++i)
                res["x" + (i ? (i + 1) : "") + "axis"] = xaxes[i] || {};
            for (i = 0; i < yaxes.length; ++i)
                res["y" + (i ? (i + 1) : "") + "axis"] = yaxes[i] || {};

            // backwards compatibility - to be removed
            if (!res.x2axis)
                res.x2axis = { n: 2 };
            if (!res.y2axis)
                res.y2axis = { n: 2 };
            
            return res;
        };
        plot.getXAxes = function () { return xaxes; };
        plot.getYAxes = function () { return yaxes; };
        plot.getUsedAxes = getUsedAxes; // return flat array with x and y axes that are in use
        plot.c2p = canvasToAxisCoords;
        plot.p2c = axisToCanvasCoords;
        plot.getOptions = function () { return options; };
        plot.highlight = highlight;
        plot.unhighlight = unhighlight;
        plot.triggerRedrawOverlay = triggerRedrawOverlay;
        plot.pointOffset = function(point) {
            return {
                left: parseInt(xaxes[axisNumber(point, "x") - 1].p2c(+point.x) + plotOffset.left),
                top: parseInt(yaxes[axisNumber(point, "y") - 1].p2c(+point.y) + plotOffset.top)
            };
        };

        // public attributes
        plot.hooks = hooks;
        
        // initialize
        initPlugins(plot);
        parseOptions(options_);
        constructCanvas();
        setData(data_);
        setupGrid();
        draw();
        bindEvents();


        function executeHooks(hook, args) {
            args = [plot].concat(args);
            for (var i = 0; i < hook.length; ++i)
                hook[i].apply(this, args);
        }

        function initPlugins() {
            for (var i = 0; i < plugins.length; ++i) {
                var p = plugins[i];
                p.init(plot);
                if (p.options)
                    $.extend(true, options, p.options);
            }
        }
        
        function parseOptions(opts) {
            var i;
            
            $.extend(true, options, opts);
            
            if (options.xaxis.color == null)
                options.xaxis.color = options.grid.color;
            if (options.yaxis.color == null)
                options.yaxis.color = options.grid.color;
            
            if (options.xaxis.tickColor == null) // backwards-compatibility
                options.xaxis.tickColor = options.grid.tickColor;
            if (options.yaxis.tickColor == null) // backwards-compatibility
                options.yaxis.tickColor = options.grid.tickColor;

            if (options.grid.borderColor == null)
                options.grid.borderColor = options.grid.color;
            if (options.grid.tickColor == null)
                options.grid.tickColor = $.color.parse(options.grid.color).scale('a', 0.22).toString();
            
            // fill in defaults in axes, copy at least always the
            // first as the rest of the code assumes it'll be there
            for (i = 0; i < Math.max(1, options.xaxes.length); ++i)
                options.xaxes[i] = $.extend(true, {}, options.xaxis, options.xaxes[i]);
            for (i = 0; i < Math.max(1, options.yaxes.length); ++i)
                options.yaxes[i] = $.extend(true, {}, options.yaxis, options.yaxes[i]);
            // backwards compatibility, to be removed in future
            if (options.xaxis.noTicks && options.xaxis.ticks == null)
                options.xaxis.ticks = options.xaxis.noTicks;
            if (options.yaxis.noTicks && options.yaxis.ticks == null)
                options.yaxis.ticks = options.yaxis.noTicks;
            if (options.x2axis) {
                options.y2axis.position = "top";
                options.xaxes[1] = options.x2axis;
            }
            if (options.y2axis) {
                if (options.y2axis.autoscaleMargin === undefined)
                    options.y2axis.autoscaleMargin = 0.02;
                options.y2axis.position = "right";
                options.yaxes[1] = options.y2axis;
            }
            if (options.grid.coloredAreas)
                options.grid.markings = options.grid.coloredAreas;
            if (options.grid.coloredAreasColor)
                options.grid.markingsColor = options.grid.coloredAreasColor;
            if (options.lines)
                $.extend(true, options.series.lines, options.lines);
            if (options.points)
                $.extend(true, options.series.points, options.points);
            if (options.bars)
                $.extend(true, options.series.bars, options.bars);
            if (options.shadowSize)
                options.series.shadowSize = options.shadowSize;

            for (i = 0; i < options.xaxes.length; ++i)
                getOrCreateAxis(xaxes, i + 1).options = options.xaxes[i];
            for (i = 0; i < options.yaxes.length; ++i)
                getOrCreateAxis(yaxes, i + 1).options = options.yaxes[i];

            // add hooks from options
            for (var n in hooks)
                if (options.hooks[n] && options.hooks[n].length)
                    hooks[n] = hooks[n].concat(options.hooks[n]);

            executeHooks(hooks.processOptions, [options]);
        }

        function setData(d) {
            series = parseData(d);
            fillInSeriesOptions();
            processData();
        }
        
        function parseData(d) {
            var res = [];
            for (var i = 0; i < d.length; ++i) {
                var s = $.extend(true, {}, options.series);

                if (d[i].data) {
                    s.data = d[i].data; // move the data instead of deep-copy
                    delete d[i].data;

                    // lables;
                    if(d[i].labels) {
                    	s.labels = d[i].labels;
                    	delete d[i].labels;
                    }
                    
                    $.extend(true, s, d[i]);

                    d[i].data = s.data;
                    d[i].labels = s.labels;
                }
                else
                    s.data = d[i];
                res.push(s);
            }

            return res;
        }
        
        function axisNumber(obj, coord) {
            var a = obj[coord + "axis"];
            if (typeof a == "object") // if we got a real axis, extract number
                a = a.n;
            if (typeof a != "number")
                a = 1; // default to first axis
            return a;
        }

        function canvasToAxisCoords(pos) {
            // return an object with x/y corresponding to all used axes 
            var res = {}, i, axis;
            for (i = 0; i < xaxes.length; ++i) {
                axis = xaxes[i];
                if (axis && axis.used)
                    res["x" + axis.n] = axis.c2p(pos.left);
            }

            for (i = 0; i < yaxes.length; ++i) {
                axis = yaxes[i];
                if (axis && axis.used)
                    res["y" + axis.n] = axis.c2p(pos.top);
            }
            
            if (res.x1 !== undefined)
                res.x = res.x1;
            if (res.y1 !== undefined)
                res.y = res.y1;

            return res;
        }
        
        function axisToCanvasCoords(pos) {
            // get canvas coords from the first pair of x/y found in pos
            var res = {}, i, axis, key;

            for (i = 0; i < xaxes.length; ++i) {
                axis = xaxes[i];
                if (axis && axis.used) {
                    key = "x" + axis.n;
                    if (pos[key] == null && axis.n == 1)
                        key = "x";

                    if (pos[key]) {
                        res.left = axis.p2c(pos[key]);
                        break;
                    }
                }
            }
            
            for (i = 0; i < yaxes.length; ++i) {
                axis = yaxes[i];
                if (axis && axis.used) {
                    key = "y" + axis.n;
                    if (pos[key] == null && axis.n == 1)
                        key = "y";

                    if (pos[key]) {
                        res.top = axis.p2c(pos[key]);
                        break;
                    }
                }
            }
            
            return res;
        }
        
        function getUsedAxes() {
            var res = [], i, axis;
            for (i = 0; i < xaxes.length; ++i) {
                axis = xaxes[i];
                if (axis && axis.used)
                    res.push(axis);
            }
            for (i = 0; i < yaxes.length; ++i) {
                axis = yaxes[i];
                if (axis && axis.used)
                    res.push(axis);
            }
            return res;
        }

        function getOrCreateAxis(axes, number) {
            if (!axes[number - 1])
                axes[number - 1] = {
                    n: number, // save the number for future reference
                    direction: axes == xaxes ? "x" : "y",
                    options: $.extend(true, {}, axes == xaxes ? options.xaxis : options.yaxis)
                };
                
            return axes[number - 1];
        }

        function fillInSeriesOptions() {
            var i;
            
            // collect what we already got of colors
            var neededColors = series.length,
                usedColors = [],
                assignedColors = [];
            for (i = 0; i < series.length; ++i) {
                var sc = series[i].color;
                if (sc != null) {
                    --neededColors;
                    if (typeof sc == "number")
                        assignedColors.push(sc);
                    else
                        usedColors.push($.color.parse(series[i].color));
                }
            }
            
            // we might need to generate more colors if higher indices
            // are assigned
            for (i = 0; i < assignedColors.length; ++i) {
                neededColors = Math.max(neededColors, assignedColors[i] + 1);
            }

            // produce colors as needed
            var colors = [], variation = 0;
            i = 0;
            while (colors.length < neededColors) {
                var c;
                if (options.colors.length == i) // check degenerate case
                    c = $.color.make(100, 100, 100);
                else
                    c = $.color.parse(options.colors[i]);

                // vary color if needed
                var sign = variation % 2 == 1 ? -1 : 1;
                c.scale('rgb', 1 + sign * Math.ceil(variation / 2) * 0.2)

                // FIXME: if we're getting to close to something else,
                // we should probably skip this one
                colors.push(c);
                
                ++i;
                if (i >= options.colors.length) {
                    i = 0;
                    ++variation;
                }
            }

            // fill in the options
            var colori = 0, s;
            for (i = 0; i < series.length; ++i) {
                s = series[i];
                
                // assign colors
                if (s.color == null) {
                    s.color = colors[colori].toString();
                    ++colori;
                }
                else if (typeof s.color == "number")
                    s.color = colors[s.color].toString();

                // turn on lines automatically in case nothing is set
                if (s.lines.show == null) {
                    var v, show = true;
                    for (v in s)
                        if (s[v] && s[v].show) {
                            show = false;
                            break;
                        }
                    if (show)
                        s.lines.show = true;
                }

                // setup axes
                s.xaxis = getOrCreateAxis(xaxes, axisNumber(s, "x"));
                s.yaxis = getOrCreateAxis(yaxes, axisNumber(s, "y"));
            }
        }
        
        function processData() {
            var topSentry = Number.POSITIVE_INFINITY,
                bottomSentry = Number.NEGATIVE_INFINITY,
                i, j, k, m, length,
                s, points, ps, x, y, axis, val, f, p;

            function initAxis(axis, number) {
                if (!axis)
                    return;
                
                axis.datamin = topSentry;
                axis.datamax = bottomSentry;
                axis.used = false;
            }

            function updateAxis(axis, min, max) {
                if (min < axis.datamin)
                    axis.datamin = min;
                if (max > axis.datamax)
                    axis.datamax = max;
            }

            for (i = 0; i < xaxes.length; ++i)
                initAxis(xaxes[i]);
            for (i = 0; i < yaxes.length; ++i)
                initAxis(yaxes[i]);
            
            for (i = 0; i < series.length; ++i) {
                s = series[i];
                s.datapoints = { points: [] };
                
                executeHooks(hooks.processRawData, [ s, s.data, s.datapoints ]);
            }
            
            // first pass: clean and copy data
            for (i = 0; i < series.length; ++i) {
                s = series[i];

                var data = s.data, format = s.datapoints.format;

                if (!format) {
                    format = [];
                    // find out how to copy
                    format.push({ x: true, number: true, required: true });
                    format.push({ y: true, number: true, required: true });

                    if (s.bars.show || (s.lines.show && s.lines.fill)) {
                        format.push({ y: true, number: true, required: false, defaultValue: 0 });
                        if (s.bars.horizontal) {
                            delete format[format.length - 1].y;
                            format[format.length - 1].x = true;
                        }
                    }
                    
                    s.datapoints.format = format;
                }

                if (s.datapoints.pointsize != null)
                    continue; // already filled in

                s.datapoints.pointsize = format.length;
                
                ps = s.datapoints.pointsize;
                points = s.datapoints.points;

                insertSteps = s.lines.show && s.lines.steps;
                s.xaxis.used = s.yaxis.used = true;
                
                for (j = k = 0; j < data.length; ++j, k += ps) {
                    p = data[j];

                    var nullify = p == null;
                    if (!nullify) {
                        for (m = 0; m < ps; ++m) {
                            val = p[m];
                            f = format[m];

                            if (f) {
                                if (f.number && val != null) {
                                    val = +val; // convert to number
                                    if (isNaN(val))
                                        val = null;
                                }

                                if (val == null) {
                                    if (f.required)
                                        nullify = true;
                                    
                                    if (f.defaultValue != null)
                                        val = f.defaultValue;
                                }
                            }
                            
                            points[k + m] = val;
                        }
                    }
                    
                    if (nullify) {
                        for (m = 0; m < ps; ++m) {
                            val = points[k + m];
                            if (val != null) {
                                f = format[m];
                                // extract min/max info
                                if (f.x)
                                    updateAxis(s.xaxis, val, val);
                                if (f.y)
                                    updateAxis(s.yaxis, val, val);
                            }
                            points[k + m] = null;
                        }
                    }
                    else {
                        // a little bit of line specific stuff that
                        // perhaps shouldn't be here, but lacking
                        // better means...
                        if (insertSteps && k > 0
                            && points[k - ps] != null
                            && points[k - ps] != points[k]
                            && points[k - ps + 1] != points[k + 1]) {
                            // copy the point to make room for a middle point
                            for (m = 0; m < ps; ++m)
                                points[k + ps + m] = points[k + m];

                            // middle point has same y
                            points[k + 1] = points[k - ps + 1];

                            // we've added a point, better reflect that
                            k += ps;
                        }
                    }
                }
            }

            // give the hooks a chance to run
            for (i = 0; i < series.length; ++i) {
                s = series[i];
                
                executeHooks(hooks.processDatapoints, [ s, s.datapoints]);
            }

            // second pass: find datamax/datamin for auto-scaling
            for (i = 0; i < series.length; ++i) {
                s = series[i];
                points = s.datapoints.points,
                ps = s.datapoints.pointsize;

                var xmin = topSentry, ymin = topSentry,
                    xmax = bottomSentry, ymax = bottomSentry;
                
                for (j = 0; j < points.length; j += ps) {
                    if (points[j] == null)
                        continue;

                    for (m = 0; m < ps; ++m) {
                        val = points[j + m];
                        f = format[m];
                        if (!f)
                            continue;
                        
                        if (f.x) {
                            if (val < xmin)
                                xmin = val;
                            if (val > xmax)
                                xmax = val;
                        }
                        if (f.y) {
                            if (val < ymin)
                                ymin = val;
                            if (val > ymax)
                                ymax = val;
                        }
                    }
                }
                
                if (s.bars.show) {
                    // make sure we got room for the bar on the dancing floor
                    var delta = s.bars.align == "left" ? 0 : -s.bars.barWidth/2;
                    if (s.bars.horizontal) {
                        ymin += delta;
                        ymax += delta + s.bars.barWidth;
                    }
                    else {
                        xmin += delta;
                        xmax += delta + s.bars.barWidth;
                    }
                }
                
                updateAxis(s.xaxis, xmin, xmax);
                updateAxis(s.yaxis, ymin, ymax);
            }

            $.each(getUsedAxes(), function (i, axis) {
                if (axis.datamin == topSentry)
                    axis.datamin = null;
                if (axis.datamax == bottomSentry)
                    axis.datamax = null;
            });
        }

        function constructCanvas() {
            function makeCanvas(width, height) {
                var c = document.createElement('canvas');
                c.width = width;
                c.height = height;
                if (!c.getContext) // excanvas hack
                    c = window.G_vmlCanvasManager.initElement(c);
                return c;
            }
            
            canvasWidth = placeholder.width();
            canvasHeight = placeholder.height();
            placeholder.html(""); // clear placeholder
            if (placeholder.css("position") == 'static')
                placeholder.css("position", "relative"); // for positioning labels and overlay

            if (canvasWidth <= 0 || canvasHeight <= 0)
                throw "Invalid dimensions for plot, width = " + canvasWidth + ", height = " + canvasHeight;

            if (window.G_vmlCanvasManager) // excanvas hack
                window.G_vmlCanvasManager.init_(document); // make sure everything is setup
            
            // the canvas
            canvas = $(makeCanvas(canvasWidth, canvasHeight)).appendTo(placeholder).get(0);
            ctx = canvas.getContext("2d");

            // overlay canvas for interactive features
            overlay = $(makeCanvas(canvasWidth, canvasHeight)).css({ position: 'absolute', left: 0, top: 0 }).appendTo(placeholder).get(0);
            octx = overlay.getContext("2d");
            octx.stroke();
        }

        function bindEvents() {
            // we include the canvas in the event holder too, because IE 7
            // sometimes has trouble with the stacking order
            eventHolder = $([overlay, canvas]);

            // bind events
            if (options.grid.hoverable)
                eventHolder.mousemove(onMouseMove);

            if (options.grid.clickable)
                eventHolder.click(onClick);

            executeHooks(hooks.bindEvents, [eventHolder]);
        }

        function setTransformationHelpers(axis) {
            // set helper functions on the axis, assumes plot area
            // has been computed already
            
            function identity(x) { return x; }
            
            var s, m, t = axis.options.transform || identity,
                it = axis.options.inverseTransform;
            
            if (axis.direction == "x") {
                // precompute how much the axis is scaling a point
                // in canvas space
                s = axis.scale = plotWidth / (t(axis.max) - t(axis.min));
                m = t(axis.min);

                // data point to canvas coordinate
                if (t == identity) // slight optimization
                    axis.p2c = function (p) { return (p - m) * s; };
                else
                    axis.p2c = function (p) { return (t(p) - m) * s; };
                // canvas coordinate to data point
                if (!it)
                    axis.c2p = function (c) { return m + c / s; };
                else
                    axis.c2p = function (c) { return it(m + c / s); };
            }
            else {
                s = axis.scale = plotHeight / (t(axis.max) - t(axis.min));
                m = t(axis.max);
                
                if (t == identity)
                    axis.p2c = function (p) { return (m - p) * s; };
                else
                    axis.p2c = function (p) { return (m - t(p)) * s; };
                if (!it)
                    axis.c2p = function (c) { return m - c / s; };
                else
                    axis.c2p = function (c) { return it(m - c / s); };
            }
        }

        function measureTickLabels(axis) {
            if (!axis)
                return;
            
            var opts = axis.options, i, ticks = axis.ticks || [], labels = [],
                l, w = opts.labelWidth, h = opts.labelHeight, dummyDiv;

            function makeDummyDiv(labels, width) {
                return $('<div style="position:absolute;top:-10000px;' + width + 'font-size:smaller">' +
                         '<div class="' + axis.direction + 'Axis ' + axis.direction + axis.n + 'Axis">'
                         + labels.join("") + '</div></div>')
                    .appendTo(placeholder);
            }
            
            if (axis.direction == "x") {
                // to avoid measuring the widths of the labels (it's slow), we
                // construct fixed-size boxes and put the labels inside
                // them, we don't need the exact figures and the
                // fixed-size box content is easy to center
                if (w == null)
                    w = Math.floor(canvasWidth / (ticks.length > 0 ? ticks.length : 1));

                // measure x label heights
                if (h == null) {
                    labels = [];
                    for (i = 0; i < ticks.length; ++i) {
                        l = ticks[i].label;
                        if (l)
                            labels.push('<div class="tickLabel" style="float:left;width:' + w + 'px">' + l + '</div>');
                    }

                    if (labels.length > 0) {
                        // stick them all in the same div and measure
                        // collective height
                        labels.push('<div style="clear:left"></div>');
                        dummyDiv = makeDummyDiv(labels, "width:10000px;");
                        h = dummyDiv.height();
                        dummyDiv.remove();
                    }
                }
            }
            else if (w == null || h == null) {
                // calculate y label dimensions
                for (i = 0; i < ticks.length; ++i) {
                    l = ticks[i].label;
                    if (l)
                        labels.push('<div class="tickLabel">' + l + '</div>');
                }
                
                if (labels.length > 0) {
                    dummyDiv = makeDummyDiv(labels, "");
                    if (w == null)
                        w = dummyDiv.children().width();
                    if (h == null)
                        h = dummyDiv.find("div.tickLabel").height();
                    dummyDiv.remove();
                }
            }

            if (w == null)
                w = 0;
            if (h == null)
                h = 0;
            
            axis.labelWidth = w;
            axis.labelHeight = h;
        }

        function computeAxisBox(axis) {
            if (!axis || (!axis.used && !(axis.labelWidth || axis.labelHeight)))
                return;

            // find the bounding box of the axis by looking at label
            // widths/heights and ticks, make room by diminishing the
            // plotOffset

            var lw = axis.labelWidth,
                lh = axis.labelHeight,
                pos = axis.options.position,
                tickLength = axis.options.tickLength,
                axismargin = options.grid.axisMargin,
                padding = options.grid.labelMargin,
                all = axis.direction == "x" ? xaxes : yaxes,
                index;

            // determine axis margin
            var samePosition = $.grep(all, function (a) {
                return a && a.options.position == pos && (a.labelHeight || a.labelWidth);
            });
            if ($.inArray(axis, samePosition) == samePosition.length - 1)
                axismargin = 0; // outermost

            // determine tick length - if we're innermost, we can use "full"
            if (tickLength == null)
                tickLength = "full";

            var sameDirection = $.grep(all, function (a) {
                return a && (a.labelHeight || a.labelWidth);
            });

            var innermost = $.inArray(axis, sameDirection) == 0;
            if (!innermost && tickLength == "full")
                tickLength = 5;
                
            if (!isNaN(+tickLength))
                padding += +tickLength;

            // compute box
            if (axis.direction == "x") {
                lh += padding;
                
                if (pos == "bottom") {
                    plotOffset.bottom += lh + axismargin;
                    axis.box = { top: canvasHeight - plotOffset.bottom, height: lh };
                }
                else {
                    axis.box = { top: plotOffset.top + axismargin, height: lh };
                    plotOffset.top += lh + axismargin;
                }
            }
            else {
                lw += padding;
                
                if (pos == "left") {
                    axis.box = { left: plotOffset.left + axismargin, width: lw };
                    plotOffset.left += lw + axismargin;
                }
                else {
                    plotOffset.right += lw + axismargin;
                    axis.box = { left: canvasWidth - plotOffset.right, width: lw };
                }
            }

             // save for future reference
            axis.position = pos;
            axis.tickLength = tickLength;
            axis.box.padding = padding;
            axis.innermost = innermost;
        }

        function fixupAxisBox(axis) {
            // set remaining bounding box coordinates
            if (axis.direction == "x") {
                axis.box.left = plotOffset.left;
                axis.box.width = plotWidth;
            }
            else {
                axis.box.top = plotOffset.top;
                axis.box.height = plotHeight;
            }
        }
        
        function setupGrid() {
            var axes = getUsedAxes(), j, k;

            // compute axis intervals
            for (k = 0; k < axes.length; ++k)
                setRange(axes[k]);

            
            plotOffset.left = plotOffset.right = plotOffset.top = plotOffset.bottom = 0;
            if (options.grid.show) {
                // make the ticks
                for (k = 0; k < axes.length; ++k) {
                    setupTickGeneration(axes[k]);
                    setTicks(axes[k]);
                    snapRangeToTicks(axes[k], axes[k].ticks);
                }

                // find labelWidth/Height, do this on all, not just
                // used as we might need to reserve space for unused
                // too if their labelWidth/Height is set
                for (j = 0; j < xaxes.length; ++j)
                    measureTickLabels(xaxes[j]);
                for (j = 0; j < yaxes.length; ++j)
                    measureTickLabels(yaxes[j]);
                    
                // compute the axis boxes, start from the outside (reverse order)
                for (j = xaxes.length - 1; j >= 0; --j)
                    computeAxisBox(xaxes[j]);
                for (j = yaxes.length - 1; j >= 0; --j)
                    computeAxisBox(yaxes[j]);

                // make sure we've got enough space for things that
                // might stick out
                var maxOutset = 0;
                for (var i = 0; i < series.length; ++i)
                    maxOutset = Math.max(maxOutset, 2 * (series[i].points.radius + series[i].points.lineWidth/2));

                for (var a in plotOffset) {
                    plotOffset[a] += options.grid.borderWidth;
                    plotOffset[a] = Math.max(maxOutset, plotOffset[a]);
                }
            }
            
            plotWidth = canvasWidth - plotOffset.left - plotOffset.right;
            plotHeight = canvasHeight - plotOffset.bottom - plotOffset.top;
            
            // now we got the proper plotWidth/Height, we can compute the scaling
            for (k = 0; k < axes.length; ++k)
                setTransformationHelpers(axes[k]);

            if (options.grid.show) {
                for (k = 0; k < axes.length; ++k)
                    fixupAxisBox(axes[k]);
                
                insertAxisLabels();
            }
            
            insertLegend();
        }
        
        function setRange(axis) {
            var opts = axis.options,
                min = +(opts.min != null ? opts.min : axis.datamin),
                max = +(opts.max != null ? opts.max : axis.datamax),
                delta = max - min;

            if (delta == 0.0) {
                // degenerate case
                var widen = max == 0 ? 1 : 0.01;

                if (opts.min == null)
                    min -= widen;
                // alway widen max if we couldn't widen min to ensure we
                // don't fall into min == max which doesn't work
                if (opts.max == null || opts.min != null)
                    max += widen;
            }
            else {
                // consider autoscaling
                var margin = opts.autoscaleMargin;
                if (margin != null) {
                    if (opts.min == null) {
                        min -= delta * margin;
                        // make sure we don't go below zero if all values
                        // are positive
                        if (min < 0 && axis.datamin != null && axis.datamin >= 0)
                            min = 0;
                    }
                    if (opts.max == null) {
                        max += delta * margin;
                        if (max > 0 && axis.datamax != null && axis.datamax <= 0)
                            max = 0;
                    }
                }
            }
            axis.min = min;
            axis.max = max;
            
            // add extra space for labels to axis.max if this is the y-axis.
            if(axis.direction == "y" && options.series.peaks.show) {
            	axis.max = axis.max + ((axis.max - axis.min) / canvasHeight ) * 20;
            }
        }

        function setupTickGeneration(axis) {
            var opts = axis.options;
                
            // estimate number of ticks
            var noTicks;
            if (typeof opts.ticks == "number" && opts.ticks > 0)
                noTicks = opts.ticks;
            else if (axis.direction == "x")
                 // heuristic based on the model a*sqrt(x) fitted to
                 // some reasonable data points
                noTicks = 0.3 * Math.sqrt(canvasWidth);
            else
                noTicks = 0.3 * Math.sqrt(canvasHeight);

            var delta = (axis.max - axis.min) / noTicks,
                size, generator, unit, formatter, i, magn, norm;

            if (opts.mode == "time") {
                // pretty handling of time
                
                // map of app. size of time units in milliseconds
                var timeUnitSize = {
                    "second": 1000,
                    "minute": 60 * 1000,
                    "hour": 60 * 60 * 1000,
                    "day": 24 * 60 * 60 * 1000,
                    "month": 30 * 24 * 60 * 60 * 1000,
                    "year": 365.2425 * 24 * 60 * 60 * 1000
                };


                // the allowed tick sizes, after 1 year we use
                // an integer algorithm
                var spec = [
                    [1, "second"], [2, "second"], [5, "second"], [10, "second"],
                    [30, "second"], 
                    [1, "minute"], [2, "minute"], [5, "minute"], [10, "minute"],
                    [30, "minute"], 
                    [1, "hour"], [2, "hour"], [4, "hour"],
                    [8, "hour"], [12, "hour"],
                    [1, "day"], [2, "day"], [3, "day"],
                    [0.25, "month"], [0.5, "month"], [1, "month"],
                    [2, "month"], [3, "month"], [6, "month"],
                    [1, "year"]
                ];

                var minSize = 0;
                if (opts.minTickSize != null) {
                    if (typeof opts.tickSize == "number")
                        minSize = opts.tickSize;
                    else
                        minSize = opts.minTickSize[0] * timeUnitSize[opts.minTickSize[1]];
                }

                for (var i = 0; i < spec.length - 1; ++i)
                    if (delta < (spec[i][0] * timeUnitSize[spec[i][1]]
                                 + spec[i + 1][0] * timeUnitSize[spec[i + 1][1]]) / 2
                       && spec[i][0] * timeUnitSize[spec[i][1]] >= minSize)
                        break;
                size = spec[i][0];
                unit = spec[i][1];
                
                // special-case the possibility of several years
                if (unit == "year") {
                    magn = Math.pow(10, Math.floor(Math.log(delta / timeUnitSize.year) / Math.LN10));
                    norm = (delta / timeUnitSize.year) / magn;
                    if (norm < 1.5)
                        size = 1;
                    else if (norm < 3)
                        size = 2;
                    else if (norm < 7.5)
                        size = 5;
                    else
                        size = 10;

                    size *= magn;
                }

                axis.tickSize = opts.tickSize || [size, unit];
                
                generator = function(axis) {
                    var ticks = [],
                        tickSize = axis.tickSize[0], unit = axis.tickSize[1],
                        d = new Date(axis.min);
                    
                    var step = tickSize * timeUnitSize[unit];

                    if (unit == "second")
                        d.setUTCSeconds(floorInBase(d.getUTCSeconds(), tickSize));
                    if (unit == "minute")
                        d.setUTCMinutes(floorInBase(d.getUTCMinutes(), tickSize));
                    if (unit == "hour")
                        d.setUTCHours(floorInBase(d.getUTCHours(), tickSize));
                    if (unit == "month")
                        d.setUTCMonth(floorInBase(d.getUTCMonth(), tickSize));
                    if (unit == "year")
                        d.setUTCFullYear(floorInBase(d.getUTCFullYear(), tickSize));
                    
                    // reset smaller components
                    d.setUTCMilliseconds(0);
                    if (step >= timeUnitSize.minute)
                        d.setUTCSeconds(0);
                    if (step >= timeUnitSize.hour)
                        d.setUTCMinutes(0);
                    if (step >= timeUnitSize.day)
                        d.setUTCHours(0);
                    if (step >= timeUnitSize.day * 4)
                        d.setUTCDate(1);
                    if (step >= timeUnitSize.year)
                        d.setUTCMonth(0);


                    var carry = 0, v = Number.NaN, prev;
                    do {
                        prev = v;
                        v = d.getTime();
                        ticks.push(v);
                        if (unit == "month") {
                            if (tickSize < 1) {
                                // a bit complicated - we'll divide the month
                                // up but we need to take care of fractions
                                // so we don't end up in the middle of a day
                                d.setUTCDate(1);
                                var start = d.getTime();
                                d.setUTCMonth(d.getUTCMonth() + 1);
                                var end = d.getTime();
                                d.setTime(v + carry * timeUnitSize.hour + (end - start) * tickSize);
                                carry = d.getUTCHours();
                                d.setUTCHours(0);
                            }
                            else
                                d.setUTCMonth(d.getUTCMonth() + tickSize);
                        }
                        else if (unit == "year") {
                            d.setUTCFullYear(d.getUTCFullYear() + tickSize);
                        }
                        else
                            d.setTime(v + step);
                    } while (v < axis.max && v != prev);

                    return ticks;
                };

                formatter = function (v, axis) {
                    var d = new Date(v);

                    // first check global format
                    if (opts.timeformat != null)
                        return $.plot.formatDate(d, opts.timeformat, opts.monthNames);
                    
                    var t = axis.tickSize[0] * timeUnitSize[axis.tickSize[1]];
                    var span = axis.max - axis.min;
                    var suffix = (opts.twelveHourClock) ? " %p" : "";
                    
                    if (t < timeUnitSize.minute)
                        fmt = "%h:%M:%S" + suffix;
                    else if (t < timeUnitSize.day) {
                        if (span < 2 * timeUnitSize.day)
                            fmt = "%h:%M" + suffix;
                        else
                            fmt = "%b %d %h:%M" + suffix;
                    }
                    else if (t < timeUnitSize.month)
                        fmt = "%b %d";
                    else if (t < timeUnitSize.year) {
                        if (span < timeUnitSize.year)
                            fmt = "%b";
                        else
                            fmt = "%b %y";
                    }
                    else
                        fmt = "%y";
                    
                    return $.plot.formatDate(d, fmt, opts.monthNames);
                };
            }
            else {
                // pretty rounding of base-10 numbers
                var maxDec = opts.tickDecimals;
                var dec = -Math.floor(Math.log(delta) / Math.LN10);
                if (maxDec != null && dec > maxDec)
                    dec = maxDec;

                magn = Math.pow(10, -dec);
                norm = delta / magn; // norm is between 1.0 and 10.0
                
                if (norm < 1.5)
                    size = 1;
                else if (norm < 3) {
                    size = 2;
                    // special case for 2.5, requires an extra decimal
                    if (norm > 2.25 && (maxDec == null || dec + 1 <= maxDec)) {
                        size = 2.5;
                        ++dec;
                    }
                }
                else if (norm < 7.5)
                    size = 5;
                else
                    size = 10;

                size *= magn;
                
                if (opts.minTickSize != null && size < opts.minTickSize)
                    size = opts.minTickSize;

                axis.tickDecimals = Math.max(0, maxDec != null ? maxDec : dec);
                axis.tickSize = opts.tickSize || size;

                generator = function (axis) {
                    var ticks = [];

                    // spew out all possible ticks
                    var start = floorInBase(axis.min, axis.tickSize),
                        i = 0, v = Number.NaN, prev;
                    do {
                        prev = v;
                        v = start + i * axis.tickSize;
                        ticks.push(v);
                        ++i;
                    } while (v < axis.max && v != prev);
                    return ticks;
                };

                formatter = function (v, axis) {
                    return v.toFixed(axis.tickDecimals);
                };
            }

            if (opts.alignTicksWithAxis != null) {
                var otherAxis = (axis.direction == "x" ? xaxes : yaxes)[opts.alignTicksWithAxis - 1];
                if (otherAxis && otherAxis.used && otherAxis != axis) {
                    // consider snapping min/max to outermost nice ticks
                    var niceTicks = generator(axis);
                    if (niceTicks.length > 0) {
                        if (opts.min == null)
                            axis.min = Math.min(axis.min, niceTicks[0]);
                        if (opts.max == null && niceTicks.length > 1)
                            axis.max = Math.max(axis.max, niceTicks[niceTicks.length - 1]);
                    }
                    
                    generator = function (axis) {
                        // copy ticks, scaled to this axis
                        var ticks = [], v, i;
                        for (i = 0; i < otherAxis.ticks.length; ++i) {
                            v = (otherAxis.ticks[i].v - otherAxis.min) / (otherAxis.max - otherAxis.min);
                            v = axis.min + v * (axis.max - axis.min);
                            ticks.push(v);
                        }
                        return ticks;
                    };
                    
                    // we might need an extra decimal since forced
                    // ticks don't necessarily fit naturally
                    if (axis.mode != "time" && opts.tickDecimals == null) {
                        var extraDec = Math.max(0, -Math.floor(Math.log(delta) / Math.LN10) + 1),
                            ts = generator(axis);

                        // only proceed if the tick interval rounded
                        // with an extra decimal doesn't give us a
                        // zero at end
                        if (!(ts.length > 1 && /\..*0$/.test((ts[1] - ts[0]).toFixed(extraDec))))
                            axis.tickDecimals = extraDec;
                    }
                }
            }

            axis.tickGenerator = generator;
            if ($.isFunction(opts.tickFormatter))
                axis.tickFormatter = function (v, axis) { return "" + opts.tickFormatter(v, axis); };
            else
                axis.tickFormatter = formatter;
        }
        
        function setTicks(axis) {
            axis.ticks = [];

            var oticks = axis.options.ticks, ticks = null;
            if (oticks == null || (typeof oticks == "number" && oticks > 0))
                ticks = axis.tickGenerator(axis);
            else if (oticks) {
                if ($.isFunction(oticks))
                    // generate the ticks
                    ticks = oticks({ min: axis.min, max: axis.max });
                else
                    ticks = oticks;
            }

            // clean up/labelify the supplied ticks, copy them over
            var i, v;
            for (i = 0; i < ticks.length; ++i) {
                var label = null;
                var t = ticks[i];
                if (typeof t == "object") {
                    v = t[0];
                    if (t.length > 1)
                        label = t[1];
                }
                else
                    v = t;
                if (label == null)
                    label = axis.tickFormatter(v, axis);
                axis.ticks[i] = { v: v, label: label };
            }
        }

        function snapRangeToTicks(axis, ticks) {
            if (axis.options.autoscaleMargin != null && ticks.length > 0) {
                // snap to ticks
                if (axis.options.min == null)
                    axis.min = Math.min(axis.min, ticks[0].v);
                if (axis.options.max == null && ticks.length > 1)
                    axis.max = Math.max(axis.max, ticks[ticks.length - 1].v);
            }
        }
      
        function draw() {
            ctx.clearRect(0, 0, canvasWidth, canvasHeight);

            var grid = options.grid;
            
            if (grid.show && !grid.aboveData)
                drawGrid();

            for (var i = 0; i < series.length; ++i) {
                executeHooks(hooks.drawSeries, [ctx, series[i]]);
                drawSeries(series[i]);
            }

            executeHooks(hooks.draw, [ctx]);
            
            if (grid.show && grid.aboveData)
                drawGrid();
        }

        function extractRange(ranges, coord) {
            var axis, from, to, axes, key;

            axes = getUsedAxes();
            for (i = 0; i < axes.length; ++i) {
                axis = axes[i];
                if (axis.direction == coord) {
                    key = coord + axis.n + "axis";
                    if (!ranges[key] && axis.n == 1)
                        key = coord + "axis"; // support x1axis as xaxis
                    if (ranges[key]) {
                        from = ranges[key].from;
                        to = ranges[key].to;
                        break;
                    }
                }
            }

            // backwards-compat stuff - to be removed in future
            if (!ranges[key]) {
                axis = coord == "x" ? xaxes[0] : yaxes[0];
                from = ranges[coord + "1"];
                to = ranges[coord + "2"];
            }

            // auto-reverse as an added bonus
            if (from != null && to != null && from > to) {
                var tmp = from;
                from = to;
                to = tmp;
            }
            
            return { from: from, to: to, axis: axis };
        }
        
        function drawGrid() {
            var i;
            
            ctx.save();
            ctx.translate(plotOffset.left, plotOffset.top);

            // draw background, if any
            if (options.grid.backgroundColor) {
                ctx.fillStyle = getColorOrGradient(options.grid.backgroundColor, plotHeight, 0, "rgba(255, 255, 255, 0)");
                ctx.fillRect(0, 0, plotWidth, plotHeight);
            }

            // draw markings
            var markings = options.grid.markings;
            if (markings) {
                if ($.isFunction(markings)) {
                    var axes = plot.getAxes();
                    // xmin etc. is backwards compatibility, to be
                    // removed in the future
                    axes.xmin = axes.xaxis.min;
                    axes.xmax = axes.xaxis.max;
                    axes.ymin = axes.yaxis.min;
                    axes.ymax = axes.yaxis.max;
                    
                    markings = markings(axes);
                }

                for (i = 0; i < markings.length; ++i) {
                    var m = markings[i],
                        xrange = extractRange(m, "x"),
                        yrange = extractRange(m, "y");

                    // fill in missing
                    if (xrange.from == null)
                        xrange.from = xrange.axis.min;
                    if (xrange.to == null)
                        xrange.to = xrange.axis.max;
                    if (yrange.from == null)
                        yrange.from = yrange.axis.min;
                    if (yrange.to == null)
                        yrange.to = yrange.axis.max;

                    // clip
                    if (xrange.to < xrange.axis.min || xrange.from > xrange.axis.max ||
                        yrange.to < yrange.axis.min || yrange.from > yrange.axis.max)
                        continue;

                    xrange.from = Math.max(xrange.from, xrange.axis.min);
                    xrange.to = Math.min(xrange.to, xrange.axis.max);
                    yrange.from = Math.max(yrange.from, yrange.axis.min);
                    yrange.to = Math.min(yrange.to, yrange.axis.max);

                    if (xrange.from == xrange.to && yrange.from == yrange.to)
                        continue;

                    // then draw
                    xrange.from = xrange.axis.p2c(xrange.from);
                    xrange.to = xrange.axis.p2c(xrange.to);
                    yrange.from = yrange.axis.p2c(yrange.from);
                    yrange.to = yrange.axis.p2c(yrange.to);
                    
                    if (xrange.from == xrange.to || yrange.from == yrange.to) {
                        // draw line
                        ctx.beginPath();
                        ctx.strokeStyle = m.color || options.grid.markingsColor;
                        ctx.lineWidth = m.lineWidth || options.grid.markingsLineWidth;
                        ctx.moveTo(xrange.from, yrange.from);
                        ctx.lineTo(xrange.to, yrange.to);
                        ctx.stroke();
                    }
                    else {
                        // fill area
                        ctx.fillStyle = m.color || options.grid.markingsColor;
                        ctx.fillRect(xrange.from, yrange.to,
                                     xrange.to - xrange.from,
                                     yrange.from - yrange.to);
                    }
                }
            }
            
            // draw the ticks
            var axes = getUsedAxes(), bw = options.grid.borderWidth;

            for (var j = 0; j < axes.length; ++j) {
                var axis = axes[j], box = axis.box,
                    t = axis.tickLength, x, y, xoff, yoff;

                ctx.strokeStyle = axis.options.tickColor || $.color.parse(axis.options.color).scale('a', 0.22).toString();
                ctx.lineWidth = 1;
                
                // find the edges
                if (axis.direction == "x") {
                    x = 0;
                    if (t == "full")
                        y = (axis.position == "top" ? 0 : plotHeight);
                    else
                        y = box.top - plotOffset.top + (axis.position == "top" ? box.height : 0);
                }
                else {
                    y = 0;
                    if (t == "full")
                        x = (axis.position == "left" ? 0 : plotWidth);
                    else
                        x = box.left - plotOffset.left + (axis.position == "left" ? box.width : 0);
                }
                
                // draw tick bar
                if (!axis.innermost) {
                    ctx.beginPath();
                    xoff = yoff = 0;
                    if (axis.direction == "x")
                        xoff = plotWidth;
                    else
                        yoff = plotHeight;
                    
                    if (ctx.lineWidth == 1) {
                        x = Math.floor(x) + 0.5;
                        y = Math.floor(y) + 0.5;
                    }

                    ctx.moveTo(x, y);
                    ctx.lineTo(x + xoff, y + yoff);
                    ctx.stroke();
                }

                // draw ticks
                ctx.beginPath();
                for (i = 0; i < axis.ticks.length; ++i) {
                    var v = axis.ticks[i].v;
                    
                    xoff = yoff = 0;

                    if (v < axis.min || v > axis.max
                        // skip those lying on the axes if we got a border
                        || (t == "full" && bw > 0
                            && (v == axis.min || v == axis.max)))
                        continue;

                    if (axis.direction == "x") {
                        x = axis.p2c(v);
                        yoff = t == "full" ? -plotHeight : t;
                        
                        if (axis.position == "top")
                            yoff = -yoff;
                    }
                    else {
                        y = axis.p2c(v);
                        xoff = t == "full" ? -plotWidth : t;
                        
                        if (axis.position == "left")
                            xoff = -xoff;
                    }

                    if (ctx.lineWidth == 1) {
                        if (axis.direction == "x")
                            x = Math.floor(x) + 0.5;
                        else
                            y = Math.floor(y) + 0.5;
                    }

                    ctx.moveTo(x, y);
                    ctx.lineTo(x + xoff, y + yoff);
                }
                
                ctx.stroke();
            }
            
            
            // draw border
            if (bw) {
                ctx.lineWidth = bw;
                ctx.strokeStyle = options.grid.borderColor;
                ctx.strokeRect(-bw/2, -bw/2, plotWidth + bw, plotHeight + bw);
            }

            ctx.restore();
        }

        function insertAxisLabels() {
            placeholder.find(".tickLabels").remove();
            
            var html = ['<div class="tickLabels" style="font-size:smaller">'];

            var axes = getUsedAxes();
            for (var j = 0; j < axes.length; ++j) {
                var axis = axes[j], box = axis.box;
                //debug: html.push('<div style="position:absolute;opacity:0.10;background-color:red;left:' + box.left + 'px;top:' + box.top + 'px;width:' + box.width +  'px;height:' + box.height + 'px"></div>')
                html.push('<div class="' + axis.direction + 'Axis ' + axis.direction + axis.n + 'Axis" style="color:' + axis.options.color + '">');
                for (var i = 0; i < axis.ticks.length; ++i) {
                    var tick = axis.ticks[i];
                    if (!tick.label || tick.v < axis.min || tick.v > axis.max)
                        continue;

                    var pos = {}, align;
                    
                    if (axis.direction == "x") {
                        align = "center";
                        pos.left = Math.round(plotOffset.left + axis.p2c(tick.v) - axis.labelWidth/2);
                        if (axis.position == "bottom")
                            pos.top = box.top + box.padding;
                        else
                            pos.bottom = canvasHeight - (box.top + box.height - box.padding);
                    }
                    else {
                        pos.top = Math.round(plotOffset.top + axis.p2c(tick.v) - axis.labelHeight/2);
                        if (axis.position == "left") {
                            pos.right = canvasWidth - (box.left + box.width - box.padding)
                            align = "right";
                        }
                        else {
                            pos.left = box.left + box.padding;
                            align = "left";
                        }
                    }

                    pos.width = axis.labelWidth;

                    var style = ["position:absolute", "text-align:" + align ];
                    for (var a in pos)
                        style.push(a + ":" + pos[a] + "px")
                    
                    html.push('<div class="tickLabel" style="' + style.join(';') + '">' + tick.label + '</div>');
                }
                html.push('</div>');
            }

            html.push('</div>');

            placeholder.append(html.join(""));
        }

        function drawSeries(series) {
            if (series.lines.show)
                drawSeriesLines(series);
            if(series.peaks.show)
            	drawSeriesPeaks(series);
            if (series.bars.show)
                drawSeriesBars(series);
            if (series.points.show)
                drawSeriesPoints(series);
        }
        
        function drawSeriesPeaks(series) {
        	
        	function plotPeaks(datapoints, xoffset, yoffset, axisx, axisy) {
        		
                var points = datapoints.points,
                    ps = datapoints.pointsize;
                
                ctx.fillStyle = series.color;
                ctx.textAlign = "center";
        		ctx.font = '11px Arial';
        		if(series.labelType == 'mz')
        			ctx.font = '11px Arial';
        		
                var incr = ps;
                
                var l = -1; // peak label index
                
                var lastx_coord, lasty1_coord, lasty2_coord, lasty;
                
                for (var i = 0; i < points.length; i += ps) {
                	
                    var x = points[i], y1 = 0,
                    y2 = points[i+1], orig_y = points[i+1];
                    
                    if (x == null)
                        continue;

                    l += 1; // peak label index
                    
                    // clip with xmin
                    if (x < axisx.min) {
                        continue;
                    }

                    // clip with xmax
                    if (x > axisx.max) {
                        continue;
                    }
                    
                    // calculate the x-coordinate
                    var myx = axisx.p2c(x) + xoffset
                    var tempx = Math.round(myx);
                    if(tempx > myx)
                    	myx = tempx - 0.5;
                    else
                    	myx = tempx + 0.5;
                    
                    
                    // clip with ymin ; assume y1 always < y2
                    if (y1 < axisy.min) {
                        if (y2 < axisy.min)
                            continue;   // line segment is outside
                        y1 = axisy.min;
                    }

                    // clip with ymax ; assume y2 always > y1
                    if (y2 > axisy.max) {
                        if (y1 > axisy.max)
                            continue;
                        y2 = axisy.max;
                    }


                    var myy1 = axisy.p2c(y1) + yoffset;
                    var myy2 = axisy.p2c(y2) + yoffset;
                    
                    // If we have a label associated with the peaks we will draw them all
                    // otherwise we will draw the most intense peak at every pixel to reduce drawing time
                    if(series.labelType != 'none') {
	                	drawPeak(myx, myy1, myy2);
	                	drawLabel(myx, myy2, x, y2, axisx, axisy, l);
                    }
                    else {
                    	if(lastx_coord && lastx_coord < myx) {
	                    	// draw the most intense peak at the last coordinate
	                    	drawPeak(lastx_coord, lasty1_coord, lasty2_coord);
	                    	lasty = -1;
	                    }
                    	if(!lastx_coord || orig_y > lasty) {
                    		lastx_coord = myx;
                    		lasty1_coord = myy1;
                    		lasty2_coord = myy2;
                    		lasty = orig_y;
                    	}
                    }
                }
                
                // draw the last peak if we are only drawing most intense peaks at each pixel
                if(series.labelType == 'none') {
                	if(lastx_coord) {
                    	// draw the most intense peak at the last coordinate
                    	drawPeak(lastx_coord, lasty1_coord, lasty2_coord);
                    }
                }
                //console.log("# peaks drawn: "+l);
            }
        	
        	function drawPeak(x_coord, y1_coord, y2_coord) {
        		ctx.beginPath();
        		ctx.moveTo(x_coord, y1_coord);
                ctx.lineTo(x_coord, y2_coord);
            	ctx.stroke();
        	}
        	
        	function drawLabel(myx, myy2, x, y2, axisx, axisy, l) {
        		
        		if(series.labelType != 'none') {
            		
            		var drawLabel = true;
            		
            		if(y2 == axisy.max)
            			drawLabel = false;;
            		
            		if(drawLabel) {
                		var label = '';
                		
                		if(series.labelType == 'mz') {
                			var label = x.toFixed(2);
                		}
                		else  {
		                	if(series.labels) {
		                		//alert(myx1+", "+myx2);
		                		label = series.labels[l];
		                	}
                		}
                		if(series.peaks.print) {
                			// appending a div is too slow
                			o = plot.getPlotOffset();
	                		placeholder.append('<div style="position:absolute;left:' +(myx+o.left-2) + 'px;top:' +(myy2 - o.top - 2)  + 'px;color:'+series.color+'">'+label+'</div>');
                		}
                		else {
	                		var metrics = ctx.measureText(label);
	                		ctx.save();
	                		ctx.translate(myx, myy2)
	                		ctx.rotate(-90 * Math.PI/180);
	                		ctx.fillText(label, (metrics.width / 2)+4 ,3);
	                		ctx.restore();
                		}
            		}
            	}
        		
        	}
        	
        	ctx.save();
            ctx.translate(plotOffset.left, plotOffset.top);
            ctx.lineJoin = "round";

            var lw = series.peaks.lineWidth;
            ctx.lineWidth = lw;
            ctx.strokeStyle = series.color;
            if (lw > 0)
                plotPeaks(series.datapoints, 0, 0, series.xaxis, series.yaxis);
            ctx.restore();
        }
        
        function drawSeriesLines(series) {
            function plotLine(datapoints, xoffset, yoffset, axisx, axisy) {
                var points = datapoints.points,
                    ps = datapoints.pointsize,
                    prevx = null, prevy = null;
                
                ctx.beginPath();
                for (var i = ps; i < points.length; i += ps) {
                    var x1 = points[i - ps], y1 = points[i - ps + 1],
                        x2 = points[i], y2 = points[i + 1];
                    
                    if (x1 == null || x2 == null)
                        continue;

                    // clip with ymin
                    if (y1 <= y2 && y1 < axisy.min) {
                        if (y2 < axisy.min)
                            continue;   // line segment is outside
                        // compute new intersection point
                        x1 = (axisy.min - y1) / (y2 - y1) * (x2 - x1) + x1;
                        y1 = axisy.min;
                    }
                    else if (y2 <= y1 && y2 < axisy.min) {
                        if (y1 < axisy.min)
                            continue;
                        x2 = (axisy.min - y1) / (y2 - y1) * (x2 - x1) + x1;
                        y2 = axisy.min;
                    }

                    // clip with ymax
                    if (y1 >= y2 && y1 > axisy.max) {
                        if (y2 > axisy.max)
                            continue;
                        x1 = (axisy.max - y1) / (y2 - y1) * (x2 - x1) + x1;
                        y1 = axisy.max;
                    }
                    else if (y2 >= y1 && y2 > axisy.max) {
                        if (y1 > axisy.max)
                            continue;
                        x2 = (axisy.max - y1) / (y2 - y1) * (x2 - x1) + x1;
                        y2 = axisy.max;
                    }

                    // clip with xmin
                    if (x1 <= x2 && x1 < axisx.min) {
                        if (x2 < axisx.min)
                            continue;
                        y1 = (axisx.min - x1) / (x2 - x1) * (y2 - y1) + y1;
                        x1 = axisx.min;
                    }
                    else if (x2 <= x1 && x2 < axisx.min) {
                        if (x1 < axisx.min)
                            continue;
                        y2 = (axisx.min - x1) / (x2 - x1) * (y2 - y1) + y1;
                        x2 = axisx.min;
                    }

                    // clip with xmax
                    if (x1 >= x2 && x1 > axisx.max) {
                        if (x2 > axisx.max)
                            continue;
                        y1 = (axisx.max - x1) / (x2 - x1) * (y2 - y1) + y1;
                        x1 = axisx.max;
                    }
                    else if (x2 >= x1 && x2 > axisx.max) {
                        if (x1 > axisx.max)
                            continue;
                        y2 = (axisx.max - x1) / (x2 - x1) * (y2 - y1) + y1;
                        x2 = axisx.max;
                    }

                    if (x1 != prevx || y1 != prevy)
                        ctx.moveTo(axisx.p2c(x1) + xoffset, axisy.p2c(y1) + yoffset);
                    
                    prevx = x2;
                    prevy = y2;
                    ctx.lineTo(axisx.p2c(x2) + xoffset, axisy.p2c(y2) + yoffset);
                }
                ctx.stroke();
            }

            function plotLineArea(datapoints, axisx, axisy) {
                var points = datapoints.points,
                    ps = datapoints.pointsize,
                    bottom = Math.min(Math.max(0, axisy.min), axisy.max),
                    i = 0, top, areaOpen = false,
                    ypos = 1, segmentStart = 0, segmentEnd = 0;

                // we process each segment in two turns, first forward
                // direction to sketch out top, then once we hit the
                // end we go backwards to sketch the bottom
                while (true) {
                    if (ps > 0 && i > points.length + ps)
                        break;

                    i += ps; // ps is negative if going backwards

                    var x1 = points[i - ps],
                        y1 = points[i - ps + ypos],
                        x2 = points[i], y2 = points[i + ypos];

                    if (areaOpen) {
                        if (ps > 0 && x1 != null && x2 == null) {
                            // at turning point
                            segmentEnd = i;
                            ps = -ps;
                            ypos = 2;
                            continue;
                        }

                        if (ps < 0 && i == segmentStart + ps) {
                            // done with the reverse sweep
                            ctx.fill();
                            areaOpen = false;
                            ps = -ps;
                            ypos = 1;
                            i = segmentStart = segmentEnd + ps;
                            continue;
                        }
                    }

                    if (x1 == null || x2 == null)
                        continue;

                    // clip x values
                    
                    // clip with xmin
                    if (x1 <= x2 && x1 < axisx.min) {
                        if (x2 < axisx.min)
                            continue;
                        y1 = (axisx.min - x1) / (x2 - x1) * (y2 - y1) + y1;
                        x1 = axisx.min;
                    }
                    else if (x2 <= x1 && x2 < axisx.min) {
                        if (x1 < axisx.min)
                            continue;
                        y2 = (axisx.min - x1) / (x2 - x1) * (y2 - y1) + y1;
                        x2 = axisx.min;
                    }

                    // clip with xmax
                    if (x1 >= x2 && x1 > axisx.max) {
                        if (x2 > axisx.max)
                            continue;
                        y1 = (axisx.max - x1) / (x2 - x1) * (y2 - y1) + y1;
                        x1 = axisx.max;
                    }
                    else if (x2 >= x1 && x2 > axisx.max) {
                        if (x1 > axisx.max)
                            continue;
                        y2 = (axisx.max - x1) / (x2 - x1) * (y2 - y1) + y1;
                        x2 = axisx.max;
                    }

                    if (!areaOpen) {
                        // open area
                        ctx.beginPath();
                        ctx.moveTo(axisx.p2c(x1), axisy.p2c(bottom));
                        areaOpen = true;
                    }
                    
                    // now first check the case where both is outside
                    if (y1 >= axisy.max && y2 >= axisy.max) {
                        ctx.lineTo(axisx.p2c(x1), axisy.p2c(axisy.max));
                        ctx.lineTo(axisx.p2c(x2), axisy.p2c(axisy.max));
                        continue;
                    }
                    else if (y1 <= axisy.min && y2 <= axisy.min) {
                        ctx.lineTo(axisx.p2c(x1), axisy.p2c(axisy.min));
                        ctx.lineTo(axisx.p2c(x2), axisy.p2c(axisy.min));
                        continue;
                    }
                    
                    // else it's a bit more complicated, there might
                    // be a flat maxed out rectangle first, then a
                    // triangular cutout or reverse; to find these
                    // keep track of the current x values
                    var x1old = x1, x2old = x2;

                    // clip the y values, without shortcutting, we
                    // go through all cases in turn
                    
                    // clip with ymin
                    if (y1 <= y2 && y1 < axisy.min && y2 >= axisy.min) {
                        x1 = (axisy.min - y1) / (y2 - y1) * (x2 - x1) + x1;
                        y1 = axisy.min;
                    }
                    else if (y2 <= y1 && y2 < axisy.min && y1 >= axisy.min) {
                        x2 = (axisy.min - y1) / (y2 - y1) * (x2 - x1) + x1;
                        y2 = axisy.min;
                    }

                    // clip with ymax
                    if (y1 >= y2 && y1 > axisy.max && y2 <= axisy.max) {
                        x1 = (axisy.max - y1) / (y2 - y1) * (x2 - x1) + x1;
                        y1 = axisy.max;
                    }
                    else if (y2 >= y1 && y2 > axisy.max && y1 <= axisy.max) {
                        x2 = (axisy.max - y1) / (y2 - y1) * (x2 - x1) + x1;
                        y2 = axisy.max;
                    }

                    // if the x value was changed we got a rectangle
                    // to fill
                    if (x1 != x1old) {
                        ctx.lineTo(axisx.p2c(x1old), axisy.p2c(y1));
                        // it goes to (x1, y1), but we fill that below
                    }
                    
                    // fill triangular section, this sometimes result
                    // in redundant points if (x1, y1) hasn't changed
                    // from previous line to, but we just ignore that
                    ctx.lineTo(axisx.p2c(x1), axisy.p2c(y1));
                    ctx.lineTo(axisx.p2c(x2), axisy.p2c(y2));

                    // fill the other rectangle if it's there
                    if (x2 != x2old) {
                        ctx.lineTo(axisx.p2c(x2), axisy.p2c(y2));
                        ctx.lineTo(axisx.p2c(x2old), axisy.p2c(y2));
                    }
                }
            }

            ctx.save();
            ctx.translate(plotOffset.left, plotOffset.top);
            ctx.lineJoin = "round";

            var lw = series.lines.lineWidth,
                sw = series.shadowSize;
            // FIXME: consider another form of shadow when filling is turned on
            if (lw > 0 && sw > 0) {
                // draw shadow as a thick and thin line with transparency
                ctx.lineWidth = sw;
                ctx.strokeStyle = "rgba(0,0,0,0.1)";
                // position shadow at angle from the mid of line
                var angle = Math.PI/18;
                plotLine(series.datapoints, Math.sin(angle) * (lw/2 + sw/2), Math.cos(angle) * (lw/2 + sw/2), series.xaxis, series.yaxis);
                ctx.lineWidth = sw/2;
                plotLine(series.datapoints, Math.sin(angle) * (lw/2 + sw/4), Math.cos(angle) * (lw/2 + sw/4), series.xaxis, series.yaxis);
            }

            ctx.lineWidth = lw;
            ctx.strokeStyle = series.color;
            var fillStyle = getFillStyle(series.lines, series.color, 0, plotHeight);
            if (fillStyle) {
                ctx.fillStyle = fillStyle;
                plotLineArea(series.datapoints, series.xaxis, series.yaxis);
            }

            if (lw > 0)
                plotLine(series.datapoints, 0, 0, series.xaxis, series.yaxis);
            ctx.restore();
        }

        function drawSeriesPoints(series) {
            function plotPoints(datapoints, radius, fillStyle, offset, shadow, axisx, axisy, symbol) {
                var points = datapoints.points, ps = datapoints.pointsize;

                for (var i = 0; i < points.length; i += ps) {
                    var x = points[i], y = points[i + 1];
                    if (x == null || x < axisx.min || x > axisx.max || y < axisy.min || y > axisy.max)
                        continue;
                    
                    ctx.beginPath();
                    x = axisx.p2c(x);
                    y = axisy.p2c(y) + offset;
                    if (symbol == "circle")
                        ctx.arc(x, y, radius, 0, shadow ? Math.PI : Math.PI * 2, false);
                    else
                        symbol(ctx, x, y, radius, shadow);
                    ctx.closePath();
                    
                    if (fillStyle) {
                        ctx.fillStyle = fillStyle;
                        ctx.fill();
                    }
                    ctx.stroke();
                }
            }
            
            ctx.save();
            ctx.translate(plotOffset.left, plotOffset.top);

            var lw = series.points.lineWidth,
                sw = series.shadowSize,
                radius = series.points.radius,
                symbol = series.points.symbol;
            if (lw > 0 && sw > 0) {
                // draw shadow in two steps
                var w = sw / 2;
                ctx.lineWidth = w;
                ctx.strokeStyle = "rgba(0,0,0,0.1)";
                plotPoints(series.datapoints, radius, null, w + w/2, true,
                           series.xaxis, series.yaxis, symbol);

                ctx.strokeStyle = "rgba(0,0,0,0.2)";
                plotPoints(series.datapoints, radius, null, w/2, true,
                           series.xaxis, series.yaxis, symbol);
            }

            ctx.lineWidth = lw;
            ctx.strokeStyle = series.color;
            plotPoints(series.datapoints, radius,
                       getFillStyle(series.points, series.color), 0, false,
                       series.xaxis, series.yaxis, symbol);
            ctx.restore();
        }

        function drawBar(x, y, b, barLeft, barRight, offset, fillStyleCallback, axisx, axisy, c, horizontal, lineWidth) {
            var left, right, bottom, top,
                drawLeft, drawRight, drawTop, drawBottom,
                tmp;

            // in horizontal mode, we start the bar from the left
            // instead of from the bottom so it appears to be
            // horizontal rather than vertical
            if (horizontal) {
                drawBottom = drawRight = drawTop = true;
                drawLeft = false;
                left = b;
                right = x;
                top = y + barLeft;
                bottom = y + barRight;

                // account for negative bars
                if (right < left) {
                    tmp = right;
                    right = left;
                    left = tmp;
                    drawLeft = true;
                    drawRight = false;
                }
            }
            else {
                drawLeft = drawRight = drawTop = true;
                drawBottom = false;
                left = x + barLeft;
                right = x + barRight;
                bottom = b;
                top = y;

                // account for negative bars
                if (top < bottom) {
                    tmp = top;
                    top = bottom;
                    bottom = tmp;
                    drawBottom = true;
                    drawTop = false;
                }
            }
           
            // clip
            if (right < axisx.min || left > axisx.max ||
                top < axisy.min || bottom > axisy.max)
                return;
            
            if (left < axisx.min) {
                left = axisx.min;
                drawLeft = false;
            }

            if (right > axisx.max) {
                right = axisx.max;
                drawRight = false;
            }

            if (bottom < axisy.min) {
                bottom = axisy.min;
                drawBottom = false;
            }
            
            if (top > axisy.max) {
                top = axisy.max;
                drawTop = false;
            }

            left = axisx.p2c(left);
            bottom = axisy.p2c(bottom);
            right = axisx.p2c(right);
            top = axisy.p2c(top);
            
            // fill the bar
            if (fillStyleCallback) {
                c.beginPath();
                c.moveTo(left, bottom);
                c.lineTo(left, top);
                c.lineTo(right, top);
                c.lineTo(right, bottom);
                c.fillStyle = fillStyleCallback(bottom, top);
                c.fill();
            }

            // draw outline
            if (lineWidth > 0 && (drawLeft || drawRight || drawTop || drawBottom)) {
                c.beginPath();

                // FIXME: inline moveTo is buggy with excanvas
                c.moveTo(left, bottom + offset);
                if (drawLeft)
                    c.lineTo(left, top + offset);
                else
                    c.moveTo(left, top + offset);
                if (drawTop)
                    c.lineTo(right, top + offset);
                else
                    c.moveTo(right, top + offset);
                if (drawRight)
                    c.lineTo(right, bottom + offset);
                else
                    c.moveTo(right, bottom + offset);
                if (drawBottom)
                    c.lineTo(left, bottom + offset);
                else
                    c.moveTo(left, bottom + offset);
                c.stroke();
            }
        }
        
        function drawSeriesBars(series) {
            function plotBars(datapoints, barLeft, barRight, offset, fillStyleCallback, axisx, axisy) {
                var points = datapoints.points, ps = datapoints.pointsize;
                
                for (var i = 0; i < points.length; i += ps) {
                    if (points[i] == null)
                        continue;
                    drawBar(points[i], points[i + 1], points[i + 2], barLeft, barRight, offset, fillStyleCallback, axisx, axisy, ctx, series.bars.horizontal, series.bars.lineWidth);
                }
            }

            ctx.save();
            ctx.translate(plotOffset.left, plotOffset.top);

            // FIXME: figure out a way to add shadows (for instance along the right edge)
            ctx.lineWidth = series.bars.lineWidth;
            ctx.strokeStyle = series.color;
            var barLeft = series.bars.align == "left" ? 0 : -series.bars.barWidth/2;
            var fillStyleCallback = series.bars.fill ? function (bottom, top) { return getFillStyle(series.bars, series.color, bottom, top); } : null;
            plotBars(series.datapoints, barLeft, barLeft + series.bars.barWidth, 0, fillStyleCallback, series.xaxis, series.yaxis);
            ctx.restore();
        }

        function getFillStyle(filloptions, seriesColor, bottom, top) {
            var fill = filloptions.fill;
            if (!fill)
                return null;

            if (filloptions.fillColor)
                return getColorOrGradient(filloptions.fillColor, bottom, top, seriesColor);
            
            var c = $.color.parse(seriesColor);
            c.a = typeof fill == "number" ? fill : 0.4;
            c.normalize();
            return c.toString();
        }
        
        function insertLegend() {
            placeholder.find(".legend").remove();

            if (!options.legend.show)
                return;
            
            var fragments = [], rowStarted = false,
                lf = options.legend.labelFormatter, s, label;
            for (var i = 0; i < series.length; ++i) {
                s = series[i];
                label = s.label;
                if (!label)
                    continue;
                
                if (i % options.legend.noColumns == 0) {
                    if (rowStarted)
                        fragments.push('</tr>');
                    fragments.push('<tr>');
                    rowStarted = true;
                }

                if (lf)
                    label = lf(label, s);
                
                fragments.push(
                    '<td class="legendColorBox"><div style="border:1px solid ' + options.legend.labelBoxBorderColor + ';padding:1px"><div style="width:4px;height:0;border:5px solid ' + s.color + ';overflow:hidden"></div></div></td>' +
                    '<td class="legendLabel">' + label + '</td>');
            }
            if (rowStarted)
                fragments.push('</tr>');
            
            if (fragments.length == 0)
                return;

            var table = '<table style="font-size:smaller;color:' + options.grid.color + '">' + fragments.join("") + '</table>';
            if (options.legend.container != null)
                $(options.legend.container).html(table);
            else {
                var pos = "",
                    p = options.legend.position,
                    m = options.legend.margin;
                if (m[0] == null)
                    m = [m, m];
                if (p.charAt(0) == "n")
                    pos += 'top:' + (m[1] + plotOffset.top) + 'px;';
                else if (p.charAt(0) == "s")
                    pos += 'bottom:' + (m[1] + plotOffset.bottom) + 'px;';
                if (p.charAt(1) == "e")
                    pos += 'right:' + (m[0] + plotOffset.right) + 'px;';
                else if (p.charAt(1) == "w")
                    pos += 'left:' + (m[0] + plotOffset.left) + 'px;';
                var legend = $('<div class="legend">' + table.replace('style="', 'style="position:absolute;' + pos +';') + '</div>').appendTo(placeholder);
                if (options.legend.backgroundOpacity != 0.0) {
                    // put in the transparent background
                    // separately to avoid blended labels and
                    // label boxes
                    var c = options.legend.backgroundColor;
                    if (c == null) {
                        c = options.grid.backgroundColor;
                        if (c && typeof c == "string")
                            c = $.color.parse(c);
                        else
                            c = $.color.extract(legend, 'background-color');
                        c.a = 1;
                        c = c.toString();
                    }
                    var div = legend.children();
                    $('<div style="position:absolute;width:' + div.width() + 'px;height:' + div.height() + 'px;' + pos +'background-color:' + c + ';"> </div>').prependTo(legend).css('opacity', options.legend.backgroundOpacity);
                }
            }
        }


        // interactive features
        
        var highlights = [],
            redrawTimeout = null;
        
        // returns the data item the mouse is over, or null if none is found
        function findNearbyItem(mouseX, mouseY, seriesFilter) {
            var maxDistance = options.grid.mouseActiveRadius,
                smallestDistance = maxDistance * maxDistance + 1,
                item = null, foundPoint = false, i, j;

            for (i = series.length - 1; i >= 0; --i) {
                if (!seriesFilter(series[i]))
                    continue;
                
                var s = series[i],
                    axisx = s.xaxis,
                    axisy = s.yaxis,
                    points = s.datapoints.points,
                    ps = s.datapoints.pointsize,
                    mx = axisx.c2p(mouseX), // precompute some stuff to make the loop faster
                    my = axisy.c2p(mouseY),
                    maxx = maxDistance / axisx.scale,
                    maxy = maxDistance / axisy.scale;

                if (s.lines.show || s.points.show || s.peaks.show) {
                    for (j = 0; j < points.length; j += ps) {
                        var x = points[j], y = points[j + 1];
                        if (x == null)
                            continue;
                        
                        // For points and lines, the cursor must be within a
                        // certain distance to the data point
                        if (x - mx > maxx || x - mx < -maxx ||
                            y - my > maxy || y - my < -maxy)
                            continue;

                        // We have to calculate distances in pixels, not in
                        // data units, because the scales of the axes may be different
                        var dx = Math.abs(axisx.p2c(x) - mouseX),
                            dy = Math.abs(axisy.p2c(y) - mouseY),
                            dist = dx * dx + dy * dy; // we save the sqrt

                        // use <= to ensure last point takes precedence
                        // (last generally means on top of)
                        if (dist < smallestDistance) {
                            smallestDistance = dist;
                            item = [i, j / ps];
                        }
                    }
                }
                    
                if (s.bars.show && !item) { // no other point can be nearby
                    var barLeft = s.bars.align == "left" ? 0 : -s.bars.barWidth/2,
                        barRight = barLeft + s.bars.barWidth;
                    
                    for (j = 0; j < points.length; j += ps) {
                        var x = points[j], y = points[j + 1], b = points[j + 2];
                        if (x == null)
                            continue;
  
                        // for a bar graph, the cursor must be inside the bar
                        if (series[i].bars.horizontal ? 
                            (mx <= Math.max(b, x) && mx >= Math.min(b, x) && 
                             my >= y + barLeft && my <= y + barRight) :
                            (mx >= x + barLeft && mx <= x + barRight &&
                             my >= Math.min(b, y) && my <= Math.max(b, y)))
                                item = [i, j / ps];
                    }
                }
            }

            if (item) {
                i = item[0];
                j = item[1];
                ps = series[i].datapoints.pointsize;
                
                return { datapoint: series[i].datapoints.points.slice(j * ps, (j + 1) * ps),
                         dataIndex: j,
                         series: series[i],
                         seriesIndex: i };
            }
            
            return null;
        }

        function onMouseMove(e) {
            if (options.grid.hoverable)
                triggerClickHoverEvent("plothover", e,
                                       function (s) { return s["hoverable"] != false; });
        }
        
        function onClick(e) {
            triggerClickHoverEvent("plotclick", e,
                                   function (s) { return s["clickable"] != false; });
        }

        // trigger click or hover event (they send the same parameters
        // so we share their code)
        function triggerClickHoverEvent(eventname, event, seriesFilter) {
            var offset = eventHolder.offset(),
                canvasX = event.pageX - offset.left - plotOffset.left,
                canvasY = event.pageY - offset.top - plotOffset.top,
            pos = canvasToAxisCoords({ left: canvasX, top: canvasY });

            pos.pageX = event.pageX;
            pos.pageY = event.pageY;

            var item = findNearbyItem(canvasX, canvasY, seriesFilter);

            if (item) {
                // fill in mouse pos for any listeners out there
                item.pageX = parseInt(item.series.xaxis.p2c(item.datapoint[0]) + offset.left + plotOffset.left);
                item.pageY = parseInt(item.series.yaxis.p2c(item.datapoint[1]) + offset.top + plotOffset.top);
            }

            if (options.grid.autoHighlight) {
                // clear auto-highlights
                for (var i = 0; i < highlights.length; ++i) {
                    var h = highlights[i];
                    if (h.auto == eventname &&
                        !(item && h.series == item.series && h.point == item.datapoint))
                        unhighlight(h.series, h.point);
                }
                
                if (item)
                    highlight(item.series, item.datapoint, eventname);
            }
            
            placeholder.trigger(eventname, [ pos, item ]);
        }

        function triggerRedrawOverlay() {
            if (!redrawTimeout)
                redrawTimeout = setTimeout(drawOverlay, 30);
        }

        function drawOverlay() {
        	
            redrawTimeout = null;

            // draw highlights
            octx.save();
            octx.clearRect(0, 0, canvasWidth, canvasHeight);
            octx.translate(plotOffset.left, plotOffset.top);
            
            var i, hi;
            for (i = 0; i < highlights.length; ++i) {
                hi = highlights[i];

                if (hi.series.bars.show)
                    drawBarHighlight(hi.series, hi.point);
                else
                    drawPointHighlight(hi.series, hi.point);
            }
            octx.restore();
            
            executeHooks(hooks.drawOverlay, [octx]);
        }
        
        function highlight(s, point, auto) {
            if (typeof s == "number")
                s = series[s];

            if (typeof point == "number") {
                var ps = s.datapoints.pointsize;
                point = s.datapoints.points.slice(ps * point, ps * (point + 1));
            }

            var i = indexOfHighlight(s, point);
            if (i == -1) {
                highlights.push({ series: s, point: point, auto: auto });

                triggerRedrawOverlay();
            }
            else if (!auto)
                highlights[i].auto = false;
        }
            
        function unhighlight(s, point) {
            if (s == null && point == null) {
                highlights = [];
                triggerRedrawOverlay();
            }
            
            if (typeof s == "number")
                s = series[s];

            if (typeof point == "number")
                point = s.data[point];

            var i = indexOfHighlight(s, point);
            if (i != -1) {
                highlights.splice(i, 1);

                triggerRedrawOverlay();
            }
        }
        
        function indexOfHighlight(s, p) {
            for (var i = 0; i < highlights.length; ++i) {
                var h = highlights[i];
                if (h.series == s && h.point[0] == p[0]
                    && h.point[1] == p[1])
                    return i;
            }
            return -1;
        }
        
        function drawPointHighlight(series, point) {
            var x = point[0], y = point[1],
                axisx = series.xaxis, axisy = series.yaxis;
            
            if (x < axisx.min || x > axisx.max || y < axisy.min || y > axisy.max)
                return;
            
            var pointRadius = series.points.radius + series.points.lineWidth / 2;
            octx.lineWidth = pointRadius;
            octx.strokeStyle = $.color.parse(series.color).scale('a', 0.5).toString();
            var radius = 1.5 * pointRadius,
                x = axisx.p2c(x),
                y = axisy.p2c(y);
            
            octx.beginPath();
            if (series.points.symbol == "circle")
                octx.arc(x, y, radius, 0, 2 * Math.PI, false);
            else
                series.points.symbol(octx, x, y, radius, false);
            octx.closePath();
            octx.stroke();
        }

        function drawBarHighlight(series, point) {
            octx.lineWidth = series.bars.lineWidth;
            octx.strokeStyle = $.color.parse(series.color).scale('a', 0.5).toString();
            var fillStyle = $.color.parse(series.color).scale('a', 0.5).toString();
            var barLeft = series.bars.align == "left" ? 0 : -series.bars.barWidth/2;
            drawBar(point[0], point[1], point[2] || 0, barLeft, barLeft + series.bars.barWidth,
                    0, function () { return fillStyle; }, series.xaxis, series.yaxis, octx, series.bars.horizontal, series.bars.lineWidth);
        }

        function getColorOrGradient(spec, bottom, top, defaultColor) {
            if (typeof spec == "string")
                return spec;
            else {
                // assume this is a gradient spec; IE currently only
                // supports a simple vertical gradient properly, so that's
                // what we support too
                var gradient = ctx.createLinearGradient(0, top, 0, bottom);
                
                for (var i = 0, l = spec.colors.length; i < l; ++i) {
                    var c = spec.colors[i];
                    if (typeof c != "string") {
                        var co = $.color.parse(defaultColor);
                        if (c.brightness != null)
                            co = co.scale('rgb', c.brightness)
                        if (c.opacity != null)
                            co.a *= c.opacity;
                        c = co.toString();
                    }
                    gradient.addColorStop(i / (l - 1), c);
                }
                
                return gradient;
            }
        }
    }

    $.plot = function(placeholder, data, options) {
        //var t0 = new Date();
        var plot = new Plot($(placeholder), data, options, $.plot.plugins);
        //(window.console ? console.log : alert)("time used (msecs): " + ((new Date()).getTime() - t0.getTime()));
        return plot;
    };

    $.plot.plugins = [];

    // returns a string with the date d formatted according to fmt
    $.plot.formatDate = function(d, fmt, monthNames) {
        var leftPad = function(n) {
            n = "" + n;
            return n.length == 1 ? "0" + n : n;
        };
        
        var r = [];
        var escape = false, padNext = false;
        var hours = d.getUTCHours();
        var isAM = hours < 12;
        if (monthNames == null)
            monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

        if (fmt.search(/%p|%P/) != -1) {
            if (hours > 12) {
                hours = hours - 12;
            } else if (hours == 0) {
                hours = 12;
            }
        }
        for (var i = 0; i < fmt.length; ++i) {
            var c = fmt.charAt(i);
            
            if (escape) {
                switch (c) {
                case 'h': c = "" + hours; break;
                case 'H': c = leftPad(hours); break;
                case 'M': c = leftPad(d.getUTCMinutes()); break;
                case 'S': c = leftPad(d.getUTCSeconds()); break;
                case 'd': c = "" + d.getUTCDate(); break;
                case 'm': c = "" + (d.getUTCMonth() + 1); break;
                case 'y': c = "" + d.getUTCFullYear(); break;
                case 'b': c = "" + monthNames[d.getUTCMonth()]; break;
                case 'p': c = (isAM) ? ("" + "am") : ("" + "pm"); break;
                case 'P': c = (isAM) ? ("" + "AM") : ("" + "PM"); break;
                case '0': c = ""; padNext = true; break;
                }
                if (c && padNext) {
                    c = leftPad(c);
                    padNext = false;
                }
                r.push(c);
                if (!padNext)
                    escape = false;
            }
            else {
                if (c == "%")
                    escape = true;
                else
                    r.push(c);
            }
        }
        return r.join("");
    };
    
    // round to nearby lower multiple of base
    function floorInBase(n, base) {
        return base * Math.floor(n / base);
    }
    
})(jQuery);
/*
Flot plugin for selecting regions.

The plugin defines the following options:

  selection: {
    mode: null or "x" or "y" or "xy",
    color: color
  }

Selection support is enabled by setting the mode to one of "x", "y" or
"xy". In "x" mode, the user will only be able to specify the x range,
similarly for "y" mode. For "xy", the selection becomes a rectangle
where both ranges can be specified. "color" is color of the selection.

When selection support is enabled, a "plotselected" event will be
emitted on the DOM element you passed into the plot function. The
event handler gets a parameter with the ranges selected on the axes,
like this:

  placeholder.bind("plotselected", function(event, ranges) {
    alert("You selected " + ranges.xaxis.from + " to " + ranges.xaxis.to)
    // similar for yaxis - with multiple axes, the extra ones are in
    // x2axis, x3axis, ...
  });

The "plotselected" event is only fired when the user has finished
making the selection. A "plotselecting" event is fired during the
process with the same parameters as the "plotselected" event, in case
you want to know what's happening while it's happening,

A "plotunselected" event with no arguments is emitted when the user
clicks the mouse to remove the selection.

The plugin allso adds the following methods to the plot object:

- setSelection(ranges, preventEvent)

  Set the selection rectangle. The passed in ranges is on the same
  form as returned in the "plotselected" event. If the selection mode
  is "x", you should put in either an xaxis range, if the mode is "y"
  you need to put in an yaxis range and both xaxis and yaxis if the
  selection mode is "xy", like this:

    setSelection({ xaxis: { from: 0, to: 10 }, yaxis: { from: 40, to: 60 } });

  setSelection will trigger the "plotselected" event when called. If
  you don't want that to happen, e.g. if you're inside a
  "plotselected" handler, pass true as the second parameter. If you
  are using multiple axes, you can specify the ranges on any of those,
  e.g. as x2axis/x3axis/... instead of xaxis, the plugin picks the
  first one it sees.
  
- clearSelection(preventEvent)

  Clear the selection rectangle. Pass in true to avoid getting a
  "plotunselected" event.

- getSelection()

  Returns the current selection in the same format as the
  "plotselected" event. If there's currently no selection, the
  function returns null.

*/

(function ($) {
    function init(plot) {
        var selection = {
                first: { x: -1, y: -1}, second: { x: -1, y: -1},
                show: false,
                active: false
            };

        // FIXME: The drag handling implemented here should be
        // abstracted out, there's some similar code from a library in
        // the navigation plugin, this should be massaged a bit to fit
        // the Flot cases here better and reused. Doing this would
        // make this plugin much slimmer.
        var savedhandlers = {};

        function onMouseMove(e) {
            if (selection.active) {
                plot.getPlaceholder().trigger("plotselecting", [ getSelection() ]);

                updateSelection(e);
            }
        }

        function onMouseDown(e) {
            if (e.which != 1)  // only accept left-click
                return;
            
            // cancel out any text selections
            document.body.focus();

            // prevent text selection and drag in old-school browsers
            if (document.onselectstart !== undefined && savedhandlers.onselectstart == null) {
                savedhandlers.onselectstart = document.onselectstart;
                document.onselectstart = function () { return false; };
            }
            if (document.ondrag !== undefined && savedhandlers.ondrag == null) {
                savedhandlers.ondrag = document.ondrag;
                document.ondrag = function () { return false; };
            }

            setSelectionPos(selection.first, e);

            selection.active = true;
            
            $(document).one("mouseup", onMouseUp);
        }

        function onMouseUp(e) {
            // revert drag stuff for old-school browsers
            if (document.onselectstart !== undefined)
                document.onselectstart = savedhandlers.onselectstart;
            if (document.ondrag !== undefined)
                document.ondrag = savedhandlers.ondrag;

            // no more draggy-dee-drag
            selection.active = false;
            updateSelection(e);

            if (selectionIsSane())
                triggerSelectedEvent();
            else {
                // this counts as a clear
                plot.getPlaceholder().trigger("plotunselected", [ ]);
                plot.getPlaceholder().trigger("plotselecting", [ null ]);
            }

            return false;
        }

        function getSelection() {
            if (!selectionIsSane())
                return null;

            var r = {}, c1 = selection.first, c2 = selection.second;
            $.each(plot.getAxes(), function (name, axis) {
                if (axis.used) {
                    var p1 = axis.c2p(c1[axis.direction]), p2 = axis.c2p(c2[axis.direction]); 
                    r[name] = { from: Math.min(p1, p2), to: Math.max(p1, p2) };
                }
            });
            return r;
        }

        function triggerSelectedEvent() {
            var r = getSelection();

            plot.getPlaceholder().trigger("plotselected", [ r ]);

            // backwards-compat stuff, to be removed in future
            if (r.xaxis && r.yaxis)
                plot.getPlaceholder().trigger("selected", [ { x1: r.xaxis.from, y1: r.yaxis.from, x2: r.xaxis.to, y2: r.yaxis.to } ]);
        }

        function clamp(min, value, max) {
            return value < min ? min: (value > max ? max: value);
        }

        function setSelectionPos(pos, e) {
            var o = plot.getOptions();
            var offset = plot.getPlaceholder().offset();
            var plotOffset = plot.getPlotOffset();
            pos.x = clamp(0, e.pageX - offset.left - plotOffset.left, plot.width());
            pos.y = clamp(0, e.pageY - offset.top - plotOffset.top, plot.height());

            if (o.selection.mode == "y")
                pos.x = pos == selection.first ? 0 : plot.width();

            if (o.selection.mode == "x")
                pos.y = pos == selection.first ? 0 : plot.height();
        }

        function updateSelection(pos) {
            if (pos.pageX == null)
                return;

            setSelectionPos(selection.second, pos);
            if (selectionIsSane()) {
                selection.show = true;
                plot.triggerRedrawOverlay();
            }
            else
                clearSelection(true);
        }

        function clearSelection(preventEvent) {
            if (selection.show) {
                selection.show = false;
                plot.triggerRedrawOverlay();
                if (!preventEvent)
                    plot.getPlaceholder().trigger("plotunselected", [ ]);
            }
        }

        // taken from markings support
        function extractRange(ranges, coord) {
            var axis, from, to, axes, key;

            axes = plot.getUsedAxes();
            for (i = 0; i < axes.length; ++i) {
                axis = axes[i];
                if (axis.direction == coord) {
                    key = coord + axis.n + "axis";
                    if (!ranges[key] && axis.n == 1)
                        key = coord + "axis"; // support x1axis as xaxis
                    if (ranges[key]) {
                        from = ranges[key].from;
                        to = ranges[key].to;
                        break;
                    }
                }
            }

            // backwards-compat stuff - to be removed in future
            if (!ranges[key]) {
                axis = coord == "x" ? plot.getXAxes()[0] : plot.getYAxes()[0];
                from = ranges[coord + "1"];
                to = ranges[coord + "2"];
            }

            // auto-reverse as an added bonus
            if (from != null && to != null && from > to) {
                var tmp = from;
                from = to;
                to = tmp;
            }
            
            return { from: from, to: to, axis: axis };
        }
        
        
        function setSelection(ranges, preventEvent) {
            var axis, range, o = plot.getOptions();

            if (o.selection.mode == "y") {
                selection.first.x = 0;
                selection.second.x = plot.width();
            }
            else {
                range = extractRange(ranges, "x");

                selection.first.x = range.axis.p2c(range.from);
                selection.second.x = range.axis.p2c(range.to);
            }

            if (o.selection.mode == "x") {
                selection.first.y = 0;
                selection.second.y = plot.height();
            }
            else {
                range = extractRange(ranges, "y");

                selection.first.y = range.axis.p2c(range.from);
                selection.second.y = range.axis.p2c(range.to);
            }

            selection.show = true;
            plot.triggerRedrawOverlay();
            if (!preventEvent && selectionIsSane())
                triggerSelectedEvent();
        }

        function selectionIsSane() {
            var minSize = 5;
            return Math.abs(selection.second.x - selection.first.x) >= minSize &&
                Math.abs(selection.second.y - selection.first.y) >= minSize;
        }

        plot.clearSelection = clearSelection;
        plot.setSelection = setSelection;
        plot.getSelection = getSelection;

        plot.hooks.bindEvents.push(function(plot, eventHolder) {
            var o = plot.getOptions();
            if (o.selection.mode != null)
                eventHolder.mousemove(onMouseMove);

            if (o.selection.mode != null)
                eventHolder.mousedown(onMouseDown);
        });


        plot.hooks.drawOverlay.push(function (plot, ctx) {
        	
            // draw selection
            if (selection.show && selectionIsSane()) {
                var plotOffset = plot.getPlotOffset();
                var o = plot.getOptions();

                ctx.save();
                ctx.translate(plotOffset.left, plotOffset.top);

                var c = $.color.parse(o.selection.color);

                ctx.strokeStyle = c.scale('a', 0.8).toString();
                ctx.lineWidth = 1;
                ctx.lineJoin = "round";
                ctx.fillStyle = c.scale('a', 0.4).toString();

                var x = Math.min(selection.first.x, selection.second.x),
                    y = Math.min(selection.first.y, selection.second.y),
                    w = Math.abs(selection.second.x - selection.first.x),
                    h = Math.abs(selection.second.y - selection.first.y);

                ctx.fillRect(x, y, w, h);
                ctx.strokeRect(x, y, w, h);

                ctx.restore();
            }
        });
    }

    $.plot.plugins.push({
        init: init,
        options: {
            selection: {
                mode: null, // one of null, "x", "y" or "xy"
                color: "#F0E68C"
            }
        },
        name: 'selection',
        version: '1.0'
    });
})(jQuery);
// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

function AminoAcid(aaCode, aaShortName, aaName, monoMass, avgMass) {
   this.code = aaCode;
   this.shortName = aaShortName;
   this.name = aaName;
   this.mono = monoMass;
   this.avg = avgMass;
   
   this.get = _getAA;
}

AminoAcid.A = new AminoAcid ("A", "Ala", "Alanine",        71.037113805,  71.0779);
AminoAcid.R = new AminoAcid ("R", "Arg", "Arginine",      156.101111050, 156.18568);
AminoAcid.N = new AminoAcid ("N", "Asn", "Asparagine",    114.042927470, 114.10264);
AminoAcid.D = new AminoAcid ("D", "Asp", "Aspartic Acid", 115.026943065, 115.0874);
AminoAcid.C = new AminoAcid ("C", "Cys", "Cysteine",      103.009184505, 103.1429);
AminoAcid.E = new AminoAcid ("E", "Glu", "Glutamine",     129.042593135, 129.11398);
AminoAcid.Q = new AminoAcid ("Q", "Gln", "Glutamic Acid", 128.058577540, 128.12922);
AminoAcid.G = new AminoAcid ("G", "Gly", "Glycine",        57.021463735,  57.05132);
AminoAcid.H = new AminoAcid ("H", "His", "Histidine",     137.058911875, 137.13928);
AminoAcid.I = new AminoAcid ("I", "Ile", "Isoleucine",    113.084064015, 113.15764);
AminoAcid.L = new AminoAcid ("L", "Leu", "Leucine",       113.084064015, 113.15764);
AminoAcid.K = new AminoAcid ("K", "Lys", "Lysine",        128.094963050, 128.17228);
AminoAcid.M = new AminoAcid ("M", "Met", "Methionine",    131.040484645, 131.19606);
AminoAcid.F = new AminoAcid ("F", "Phe", "Phenylalanine", 147.068413945, 147.17386);
AminoAcid.P = new AminoAcid ("P", "Pro", "Proline",        97.052763875,  97.11518);
AminoAcid.S = new AminoAcid ("S", "Ser", "Serine",         87.032028435,  87.0773);
AminoAcid.T = new AminoAcid ("T", "Thr", "Threonine",     101.047678505, 101.10388);
AminoAcid.W = new AminoAcid ("W", "Trp", "Tryptophan",    186.079312980, 186.2099);
AminoAcid.Y = new AminoAcid ("Y", "Tyr", "Tyrosine",      163.063328575, 163.17326);
AminoAcid.V = new AminoAcid ("V", "Val", "Valine",         99.068413945,  99.13106);


AminoAcid.aa = [];
AminoAcid.aa["A"] = AminoAcid.A;
AminoAcid.aa["R"] = AminoAcid.R;
AminoAcid.aa["N"] = AminoAcid.N;
AminoAcid.aa["D"] = AminoAcid.D;
AminoAcid.aa["C"] = AminoAcid.C;
AminoAcid.aa["E"] = AminoAcid.E;
AminoAcid.aa["Q"] = AminoAcid.Q;
AminoAcid.aa["G"] = AminoAcid.G;
AminoAcid.aa["H"] = AminoAcid.H;
AminoAcid.aa["I"] = AminoAcid.I;
AminoAcid.aa["L"] = AminoAcid.L;
AminoAcid.aa["K"] = AminoAcid.K;
AminoAcid.aa["M"] = AminoAcid.M;
AminoAcid.aa["F"] = AminoAcid.F;
AminoAcid.aa["P"] = AminoAcid.P;
AminoAcid.aa["S"] = AminoAcid.S;
AminoAcid.aa["T"] = AminoAcid.T;
AminoAcid.aa["W"] = AminoAcid.W;
AminoAcid.aa["Y"] = AminoAcid.Y;
AminoAcid.aa["V"] = AminoAcid.V;

AminoAcid.get = _getAA;

function _getAA(aaCode) {
   if(AminoAcid.aa[aaCode])
      return AminoAcid.aa[aaCode];
   else
      return new AminoAcid(aaCode, aaCode, 0.0, 0.0);
}
// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

INTERNAL_ION_COLOR = "#C71585";

function InternalIon(peptide, start, end, massType, minus28) {
    var sequence = "";
    for(var i = start; i < end; i++) {
        var aa = peptide.sequence().charAt(i);
        var staticMod = peptide.staticMods()[aa];
        var variableMod = peptide.varMods()[i];
        var mod = (staticMod ? staticMod.modMass : 0) + (variableMod ? variableMod.modMass : 0);
        sequence += aa + (mod != 0 ? ("(" + mod + ")") : "");
    }
    this.sequence = sequence;
    this.subSequence = sequence;
    this.label = "<" + sequence + ">" + (minus28 ? "-CO" : ""); 
    // TODO: Verify calculation, depends on massType?   
    var massAdjust = Ion.MASS_PROTON;
    if(minus28) {
        massAdjust -= massType == "mono" ? Ion.MASS_C_12 : Ion.MASS_C;
        massAdjust -= massType == "mono" ? Ion.MASS_O_16 : Ion.MASS_O;
    }
    this.mz = peptide.getSeqMass(start, end, "n", massType) + massAdjust;
    this.massType = massType;
    this.charge = 1;
    this.internal = true;
    this.minus28 = minus28 ? true : false;
}

var getInternalIons = function(peptide, massType) {
    var seqLength = peptide.sequence().length;
    var labels = [];
    var interalIons = [];
    for(var i = 1; i < seqLength - 1; i++) {
        for(var j = i + 2; j < seqLength; j++) {
            var internalIon = new InternalIon(peptide, i, j, massType, false);
            var label = internalIon.label;
            if(!labels[label]) {
                labels[label] = true;
                interalIons.push(internalIon);
            }
            internalIon = new InternalIon(peptide, i, j, massType, true);
            label = internalIon.label;
            if(!labels[label]) {
                labels[label] = true;
                interalIons.push(internalIon);
            }
        }
    }
    sortByMz(interalIons);
    return interalIons;
}

var sortByMz = function(ionArray) {
    ionArray.sort(function(ion1, ion2) { return ion1.mz - ion2.mz;})
}// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

function Ion (t, color, charge, terminus) {
	this.type = t;
	this.color = color;
	this.charge = charge;
	this.label = this.type;
	if(this.charge > 1)
		this.label += charge;
	this.label += "+";
	this.term = terminus;
}

// Source: http://en.wikipedia.org/wiki/Web_colors

// charge +1
Ion.A_1 = new Ion("a", "#008000", 1, "n"); // green
Ion.B_1 = new Ion("b", "#0000ff", 1, "n"); // blue
Ion.C_1 = new Ion("c", "#008B8B", 1, "n"); // dark cyan
Ion.X_1 = new Ion("x", "#4B0082", 1, "c"); // indigo
Ion.Y_1 = new Ion("y", "#ff0000", 1, "c"); // red
Ion.Z_1 = new Ion("z", "#FF8C00", 1, "c"); // dark orange

// charge +2
Ion.A_2 = new Ion("a", "#2E8B57", 2, "n"); // sea green
Ion.B_2 = new Ion("b", "#4169E1", 2, "n"); // royal blue
Ion.C_2 = new Ion("c", "#20B2AA", 2, "n"); // light sea green
Ion.X_2 = new Ion("x", "#800080", 2, "c"); // purple
Ion.Y_2 = new Ion("y", "#FA8072", 2, "c"); // salmon 
Ion.Z_2 = new Ion("z", "#FFA500", 2, "c"); // orange 

// charge +3
Ion.A_3 = new Ion("a", "#9ACD32", 3, "n"); // yellow green
Ion.B_3 = new Ion("b", "#00BFFF", 3, "n"); // deep sky blue
Ion.C_3 = new Ion("c", "#66CDAA", 3, "c"); // medium aquamarine
Ion.X_3 = new Ion("x", "#9932CC", 3, "c"); // dark orchid
Ion.Y_3 = new Ion("y", "#FFA07A", 3, "c"); // light salmon
Ion.Z_3 = new Ion("z", "#FFD700", 3, "n"); // gold

Ion.MH_1 = new Ion("mh", "#2F4F4F", 1, null);
Ion.MH_2 = new Ion("mh", "#708090", 2, null);

var _ions = [];
_ions["a"] = [];
_ions["a"][1] = Ion.A_1;
_ions["a"][2] = Ion.A_2;
_ions["a"][3] = Ion.A_3;
_ions["b"] = [];
_ions["b"][1] = Ion.B_1;
_ions["b"][2] = Ion.B_2;
_ions["b"][3] = Ion.B_3;
_ions["c"] = [];
_ions["c"][1] = Ion.C_1;
_ions["c"][2] = Ion.C_2;
_ions["c"][3] = Ion.C_3;
_ions["x"] = [];
_ions["x"][1] = Ion.X_1;
_ions["x"][2] = Ion.X_2;
_ions["x"][3] = Ion.X_3;
_ions["y"] = [];
_ions["y"][1] = Ion.Y_1;
_ions["y"][2] = Ion.Y_2;
_ions["y"][3] = Ion.Y_3;
_ions["z"] = [];
_ions["z"][1] = Ion.Z_1;
_ions["z"][2] = Ion.Z_2;
_ions["z"][3] = Ion.Z_3;
_ions["mh"] = [];
_ions["mh"][1] = Ion.MH_1;
_ions["mh"][2] = Ion.MH_2;

Ion.get = function _getIon(type, charge) {
	
	return _ions[type][charge];
}

Ion.getSeriesColor = function _getSeriesColor(ion) {
	
	return _ions[ion.type][ion.charge].color;
}


//-----------------------------------------------------------------------------
// Ion Series
//-----------------------------------------------------------------------------
var MASS_H_1 = 1.00782503207;  	// H(1)  Source: http://en.wikipedia.org/wiki/Isotopes_of_hydrogen
var MASS_C_12 = 12.0;           // C(12) Source: http://en.wikipedia.org/wiki/Isotopes_of_carbon
var MASS_N_14 = 14.0030740048;  // N(14) Source: http://en.wikipedia.org/wiki/Isotopes_of_nitrogen
var MASS_O_16 = 15.99491461956; // O(16) Source: http://en.wikipedia.org/wiki/Isotopes_of_oxygen

var MASS_H = 1.00782504; // Source: http://en.wikipedia.org/wiki/Isotopes_of_hydrogen
var MASS_C = 12.0107;    // Source: http://en.wikipedia.org/wiki/Isotopes_of_carbon
var MASS_N = 14.0067;	 // Source: http://en.wikipedia.org/wiki/Isotopes_of_nitrogen
var MASS_O = 15.9994;	 // Source: http://en.wikipedia.org/wiki/Isotopes_of_oxygen

var MASS_PROTON = 1.007276;

Ion.MASS_PROTON = MASS_PROTON;
Ion.MASS_H = MASS_H;
Ion.MASS_C = MASS_C;
Ion.MASS_N = MASS_N;
Ion.MASS_O = MASS_O;
Ion.MASS_H_1 = MASS_H_1;
Ion.MASS_C_12 = MASS_C_12;
Ion.MASS_N_14 = MASS_N_14;
Ion.MASS_O_16 = MASS_O_16;

// massType can be "mono" or "avg"
Ion.getSeriesIon = function _getSeriesIon(ion, peptide, idxInSeq, massType) {
	if(ion.type == "a")	
		return new Ion_A (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "b")
		return new Ion_B (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "c")
		return new Ion_C (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "x")
		return new Ion_X (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "y")
		return new Ion_Y (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "z")
		return new Ion_Z (peptide, idxInSeq, ion.charge, massType);
	if(ion.type == "mh")
		return new Ion_MH (peptide, ion.charge, massType);
}

function _makeIonLabel(type, index, charge) {
	var label = type+""+index;
	for(var i = 1; i <= charge; i+=1) 
		label += "+";
	return label;
}

function _getMz(neutralMass, charge) {
	return ( neutralMass + (charge * MASS_PROTON) ) / charge;
}

function _getWaterLossMz(sion) {
  var massType = sion.massType;
  var mass_h = MASS_H;
  var mass_o = MASS_O;
  if(massType == "mono") {
    mass_h = MASS_H_1;
    mass_o = MASS_O_16;
  }
	var neutralMass = (sion.mz * sion.charge) - (sion.charge * MASS_PROTON);
	return _getMz((neutralMass - (mass_h * 2 + mass_o)), sion.charge);
}

function _getAmmoniaLossMz(sion) {
  var massType = sion.massType;
  var mass_h = MASS_H;
  var mass_n = MASS_O;
  if(massType == "mono") {
    mass_h = MASS_H_1;  
    mass_n = MASS_N_14;
  }
	var neutralMass = (sion.mz * sion.charge) - (sion.charge * MASS_PROTON);
	return _getMz((neutralMass - (mass_h * 3 + mass_n)), sion.charge);
}

Ion.getMz = _getMz;
Ion.getWaterLossMz = _getWaterLossMz;
Ion.getAmmoniaLossMz = _getAmmoniaLossMz;

function Ion_A (peptide, endIdxPlusOne, charge, massType) {
	// Neutral mass:  	 [N]+[M]-CHO  ; N = mass of neutral N terminal group
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(endIdxPlusOne, "n") - (MASS_C_12 + MASS_O_16);
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(endIdxPlusOne, "n") - (MASS_C + MASS_O);
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(endIdxPlusOne, "n");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("a",endIdxPlusOne, charge);
	this.match = false;
	this.term = "n";
	return this;
}

function Ion_B (peptide, endIdxPlusOne, charge, massType) {
	// Neutral mass:    [N]+[M]-H  ; N = mass of neutral N terminal group
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(endIdxPlusOne, "n");
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(endIdxPlusOne, "n");
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(endIdxPlusOne, "n");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("b", endIdxPlusOne, charge);
	this.match = false;
	this.term = "n";
	return this;
}

function Ion_C (peptide, endIdxPlusOne, charge, massType) {
	// Neutral mass:    [N]+[M]+NH2  ; N = mass of neutral N terminal group
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(endIdxPlusOne, "n") + MASS_H_1 + (MASS_N_14 + 2*MASS_H_1);
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(endIdxPlusOne, "n") + MASS_H + (MASS_N + 2*MASS_H);
  this.massType = massType;
  this.subSequence = peptide.getSubSequence(endIdxPlusOne, "n");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("c", endIdxPlusOne, charge);
	this.match = false;
	this.term = "n";
	return this;
}

function Ion_X (peptide, startIdx, charge, massType) {
	// Neutral mass = [C]+[M]+CO-H ; C = mass of neutral C-terminal group (OH)
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(startIdx, "c") + 2*MASS_O_16 + MASS_C_12;
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(startIdx, "c") + 2*MASS_O + MASS_C;
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(startIdx, "c");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("x", peptide.sequence().length - startIdx, charge);
	this.match = false;
	this.term = "c";
	return this;
}

function Ion_Y (peptide, startIdx, charge, massType) {
	// Neutral mass = [C]+[M]+H ; C = mass of neutral C-terminal group (OH)
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(startIdx, "c") + 2*MASS_H_1 + MASS_O_16;
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(startIdx, "c") + 2*MASS_H + MASS_O;
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(startIdx, "c");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
    this.label = _makeIonLabel("y", peptide.sequence().length - startIdx, charge);
	this.match = false;
	this.term = "c";
	return this;
}

function Ion_Z (peptide, startIdx, charge, massType) {
	// Neutral mass = [C]+[M]-NH2 ; C = mass of neutral C-terminal group (OH)
	// We're really printing Z-dot ions so we add an H to make it OH+[M]-NH2 +H = [M]+O-N
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getSeqMassMono(startIdx, "c") + MASS_O_16 - MASS_N_14;
	else if(massType == "avg")
		mass = peptide.getSeqMassAvg(startIdx, "c") + MASS_O - MASS_N;
	this.massType = massType;
	this.subSequence = peptide.getSubSequence(startIdx, "c");
	this.charge = charge;
	this.mz = _getMz(mass, charge);
	this.label = _makeIonLabel("z", peptide.sequence().length - startIdx, charge);
	this.match = false;
	this.term = "c";
	return this;
}

function Ion_MH (peptide, charge, massType) {
	var mass = 0;
	if(massType == "mono")
		mass = peptide.getNeutralMassMono();
	else if(massType == "avg")
		mass = peptide.getNeutralMassAvg();
	this.massType = massType;
	this.subSequence = peptide.sequence();
	this.charge = charge;
	this.mz = ( mass + (charge * MASS_PROTON) ) / charge;
	this.label = _makeIonLabel("MH", "", charge);
	this.match = false;
	this.term = null;
	return this;
}


function NeutralLoss (label, residues) {
	this.label = label;
	this.residues = residues;


	this.applies = function _applies(sion) {
		if(!this.residues) {
			return true;
		}
		if(sion.internal && sion.minus28) {
			return false;
		}
		var sequence = sion.subSequence;
		for(var i = 0; i < this.residues.length; i++) {
			if(sequence.indexOf(this.residues[i]) >= 0) {
				return true;
			}
		}
		return false;
	}
}


NeutralLoss.get = function _getNeutralLoss(label, residueSpecific) {
	if(!label) {
		return new NeutralLoss(null, null);
	} else if(label == 'nh3') {
		return new NeutralLoss('nh3', residueSpecific ? 'RKQN' : null);
	} else if(label == 'h2o') {
		return new NeutralLoss('h2o', residueSpecific ? 'STED' : null);
	}
	throw "unknown neutral loss label " + label;
}

// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

// -----------------------------------------------------------------------------
// Peptide sequence and modifications
// -----------------------------------------------------------------------------
function Peptide(seq, staticModifications, varModifications, ntermModification, ctermModification) {
	
	var sequence = seq;
	var ntermMod = ntermModification;
	var ctermMod = ctermModification;
	var staticMods = [];
	if(staticModifications) {
		for(var i = 0; i < staticModifications.length; i += 1) {
			var mod = staticModifications[i];
			staticMods[mod.aa.code] = mod;
		}
	}
	
	var varMods = [];
	if(varModifications) {
		for(var i = 0; i < varModifications.length; i += 1) {
			var mod = varModifications[i];
			varMods[mod.position] = mod;
		}
	}

    this.sequence = function () {
        return sequence;
    }

    this.varMods = function() {
        return varMods;
    }

    this.staticMods = function() {
        return staticMods;
    }

    // index: index in the seq.
    // If this is a N-term sequence we will sum up the mass of the amino acids in the sequence up-to index (exclusive).
    // If this is a C-term sequence we will sum up the mass of the amino acids in the sequence starting from index (inclusive)
    // modification masses are added
    this.getSeqMassMono = function _seqMassMono(index, term) {
        return _getSeqMass(null, index, term, "mono");
    }


    // index: index in the seq.
    // If this is a N-term sequence we will sum up the mass of the amino acids in the sequence up-to index (exclusive).
    // If this is a C-term sequence we will sum up the mass of the amino acids in the sequence starting from index (inclusive)
    // modification masses are added
    this.getSeqMassAvg = function _seqMassAvg(index, term) {
        return _getSeqMass(null, index, term, "avg");
    }

    // index: index in the seq.
    // If this is a N-term sequence we will sum up the mass of the amino acids in the sequence up-to index (exclusive).
    // If this is a C-term sequence we will sum up the mass of the amino acids in the sequence starting from index (inclusive)
    // modification masses are added
    this.getSeqMass = _getSeqMass;



    // Returns the monoisotopic neutral mass of the peptide; modifications added. N-term H and C-term OH are added
    this.getNeutralMassMono = function _massNeutralMono() {

        var mass = 0;
        var aa_obj = new AminoAcid();
        if(sequence) {
            for(var i = 0; i < sequence.length; i++) {
                var aa = aa_obj.get(sequence.charAt(i));
                mass += aa.mono;
            }
        }

        mass = _addTerminalModMass(mass, "n");
        mass = _addTerminalModMass(mass, "c");
        mass = _addResidueModMasses(mass, sequence.length, "n");
        // add N-terminal H
        mass = mass + Ion.MASS_H_1;
        // add C-terminal OH
        mass = mass + Ion.MASS_O_16 + Ion.MASS_H_1;

        return mass;
    }

    //Returns the avg neutral mass of the peptide; modifications added. N-term H and C-term OH are added
    this.getNeutralMassAvg = function _massNeutralAvg() {

        var mass = 0;
        var aa_obj = new AminoAcid();
        if(sequence) {
            for(var i = 0; i < sequence.length; i++) {
                var aa = aa_obj.get(sequence.charAt(i));
                mass += aa.avg;
            }
        }

        mass = _addTerminalModMass(mass, "n");
        mass = _addTerminalModMass(mass, "c");
        mass = _addResidueModMasses(mass, sequence.length, "n");
        // add N-terminal H
        mass = mass + Ion.MASS_H;
        // add C-terminal OH
        mass = mass + Ion.MASS_O + Ion.MASS_H;

        return mass;
    }

    function _addResidueModMasses(seqMass, slice, term) {

        var mass = seqMass;
        if(typeof(slice) == "number")
            slice = new _Slice(null, slice, term);
        for( var i = slice.from; i < slice.to; i += 1) {
            // add any static modifications
            var mod = staticMods[sequence.charAt(i)];
            if(mod) {
                mass += mod.modMass;
            }
            // add any variable modifications
            mod = varMods[i+1]; // varMods index in the sequence is 1-based
            if(mod) {
                mass += mod.modMass;
            }
        }

        return mass;
    }

    this.getSubSequence = function _getSubSeq(endIndex, term) {
        var slice = new _Slice(null, endIndex, term);
        var subSequence = ''
        if(sequence) {
            for( var i = slice.from; i < slice.to; i += 1) {
                subSequence += sequence[i];
            }
        }
        return subSequence;
    }

    function _getSeqMass(startIndex, endIndex, term, massType) {

        var mass = 0;
        var aa_obj = new AminoAcid();
        var slice = new _Slice(startIndex, endIndex, term);
        if(sequence) {
            for( var i = slice.from; i < slice.to; i += 1) {
                var aa = aa_obj.get(sequence[i]);
                mass += aa[massType];
            }
        }
        if(startIndex == null)
            mass = _addTerminalModMass(mass, term);
        mass = _addResidueModMasses(mass, slice, term);
        return mass;
    }


    function _addTerminalModMass(seqMass, term) {

        var mass = seqMass;
        // add any terminal modifications
        if(term == "n" && ntermMod)
            mass += ntermMod;
        if(term == "c" && ctermMod)
            mass += ctermMod;

        return mass;
    }

    // Defines a range or subsequence of peptide to iterate over.
    // If term is "n", than the range is from startIndex (or 0 if 
    // startIndex is null) to endIndex. If term is "c", the range is 
    // from endIndex to startIndex (or sequence.length if startIndex
    // is null).
    function _Slice(startIndex, endIndex, term) {
        if(term == "n") {
            // If N-term sense, start from begining 
            this.from = startIndex == null ? 0 : startIndex;
            this.to = endIndex;
        }
        if(term == "c") {
            this.from = endIndex;
            this.to = startIndex == null ? sequence.length : startIndex;
        }
    }
}


//-----------------------------------------------------------------------------
// Modification
//-----------------------------------------------------------------------------
function Modification(aminoAcid, mass) {
	this.aa = aminoAcid;
	this.modMass = mass;
}

function VariableModification(pos, mass, aminoAcid) {
	this.position = parseInt(pos);
	this.aa = aminoAcid;
	this.modMass = mass;
}



// $LastChangedDate$
// $LastChangedBy$
// $LastChangedRevision$

(function($) {

    // plugin name - specview
	$.fn.specview = function (opts) {

        var defaults = {
                sequence: null,
                scanNum: null,
                fileName: null,
                charge: null,
                fragmentMassType: 'mono',
                precursorMassType: 'mono',
                peakDetect: true,
                calculatedMz: null,
                precursorMz: null,
                precursorIntensity: null,
                staticMods: [],
                variableMods: [],
                ntermMod: 0, // additional mass to be added to the n-term
                ctermMod: 0, // additional mass to be added to the c-term
                peaks: [],
                sparsePeaks: null,
                ms1peaks: null,
                ms1scanLabel: null,
                precursorPeaks: null,
                precursorPeakClickFn: null,
                zoomMs1: false,
                width: 700, 	// width of the ms/ms plot
                height: 450, 	// height of the ms/ms plot
                massError: 0.5, // mass tolerance for labeling peaks
                useCookies: true,
                extraPeakSeries:[],
                residueSpecificNeutralLosses: false,
                showIonTable: true,
                showViewingOptions: true,
                showOptionsTable: true,
                showInternalIonOption: false,
                showInternalIonTable: false,
                showMHIonOption: true, //was false
                showAllTable: false,
                showSequenceInfo: true                
        };
			
	    var options = $.extend(true, {}, defaults, opts); // this is a deep copy
        var massError = options.massError;
        if(options.useCookies) {  
            var cookieMassError = readCookie('lorikeetmasserror');
            if(cookieMassError) { 
                	options.massError = parseFloat(cookieMassError);
            	}
        }

        return this.each(function() {

            index = index + 1;
            init($(this), options);

        });
	};

    var index = 0;

    var elementIds = {
            massError: "massError",
            msPlot: "msPlot",
            msmsplot: "msmsplot",
            ms1plot_zoom_out: "ms1plot_zoom_out",
            ms1plot_zoom_in: "ms1plot_zoom_in",
            ms2plot_zoom_out: "ms2plot_zoom_out",
            zoom_x: "zoom_x",
            zoom_y: "zoom_y",
            resetZoom: "resetZoom",
            update: "update",
            enableTooltip: "enableTooltip",
            msmstooltip: "lorikeet_msmstooltip",
            ion_choice: "ion_choice",
            nl_choice: "nl_choice",
            deselectIonsLink: "deselectIonsLink",
            slider_width: "slider_width",
            slider_width_val: "slider_width_val",
            slider_height: "slider_height",
            slider_height_val: "slider_height_val",
            printLink: "printLink",
            lorikeet_content: "lorikeet_content",
            optionsTable: "optionsTable",
            ionTableLoc1: "ionTableLoc1",
            ionTableLoc2: "ionTableLoc2",
            allTableLoc: "allTableLoc",
            viewOptionsDiv: "viewOptionsDiv",
            moveIonTable: "moveIonTable",
            modInfo: "modInfo",
            ionTableDiv: "ionTableDiv",
            ionTable: "ionTable",
            internalIonTable: "internalIonTable",
            fileinfo: "fileinfo",
            seqinfo: "seqinfo",
            peakDetect: "peakDetect"
	};

    function getElementId(container, elementId){
        return elementId+"_"+container.data("index");
    }

    function getElementSelector(container, elementId) {
        return "#"+getElementId(container, elementId);
    }

    function getRadioName(container, name) {
        return name+"_"+container.data("index");
    }

    function init(parent_container, options) {


        // trim any 0 intensity peaks from the end of the peaks array
        trimPeaksArray(options);

        // read the static modifications
        var parsedStaticMods = [];
        for(var i = 0; i < options.staticMods.length; i += 1) {
            var mod = options.staticMods[i];
            parsedStaticMods[i] = new Modification(AminoAcid.get(mod.aminoAcid), mod.modMass);
        }
        options.staticMods = parsedStaticMods;

        // read the variable modifications
        var parsedVarMods = [];
        for(var i = 0; i < options.variableMods.length; i += 1) {
            // position: 14, modMass: 16.0, aminoAcid: 'M'
            var mod = options.variableMods[i];
            parsedVarMods[i] = new VariableModification(
                                    mod.index,
                                    mod.modMass,
                                    AminoAcid.get(mod.aminoAcid)
                                );
        }
        options.variableMods = parsedVarMods;

        var peptide = new Peptide(options.sequence, options.staticMods, options.variableMods,
                                options.ntermMod, options.ctermMod);
        options.peptide = peptide;

        // Calculate a theoretical m/z from the given sequence and charge
        if(options.sequence && options.charge) {
            var mass = options.peptide.getNeutralMassMono();
            options.calculatedMz = Ion.getMz(mass, options.charge);
        }


        var container = createContainer(parent_container);
        // alert(container.attr('id')+" parent "+container.parent().attr('id'));
        storeContainerData(container, options);
        initContainer(container);

        if(options.charge) {
            makeOptionsTable(container, Math.max(1,options.charge-1));
        }
        else
            makeOptionsTable(container, 1);

        makeViewingOptions(container, options);

        if(options.showSequenceInfo) {
            showSequenceInfo(container, options);
            showFileInfo(container, options);
            showModInfo(container, options);
        }
        loadPlotCookies(container);
        createPlot(container, getDatasets(container)); // Initial MS/MS Plot

        if(options.ms1peaks && options.ms1peaks.length > 0) {

            var precursorMz = options.precursorMz;

            if(precursorMz)
            {
                // Find an actual peak closest to the precursor
                var diff = 5.0;
                var x, y;

                for(var i = 0; i < options.ms1peaks.length; i += 1) {
                    var pk = options.ms1peaks[i];
                    var d = Math.abs(pk[0] - precursorMz);
                    if(!diff || d < diff) {
                        x = pk[0];
                        y = pk[1];
                        diff = d;
                    }
                }
                if(diff <= 0.5) {
                    options.precursorIntensity = y;
                    if(!options.precursorPeaks)
                    {
                        options.precursorPeaks = [];
                    }
                    options.precursorPeaks.push([x,y]);
                }

                // Determine a zoom range
                if(options.zoomMs1)
                {
                    var maxIntensityInRange = 0;

                    for(var j = 0; j < options.ms1peaks.length; j += 1) {
                        var pk = options.ms1peaks[j];

                        if(pk[0] < options.precursorMz - 5.0)
                            continue;
                        if(pk[0] > options.precursorMz + 5.0)
                            break;
                        if(pk[1] > maxIntensityInRange)
                            maxIntensityInRange = pk[1];
                    }

                    options.maxIntensityInMs1ZoomRange = maxIntensityInRange;

                    // Set the zoom range
                    var ms1zoomRange = container.data("ms1zoomRange");
                    ms1zoomRange = {xaxis: {}, yaxis: {}};
                    ms1zoomRange.xaxis.from = options.precursorMz - 5.0;
                    ms1zoomRange.xaxis.to = options.precursorMz + 5.0;

                    ms1zoomRange.yaxis.from = 0.0;
                    ms1zoomRange.yaxis.to = options.maxIntensityInMs1ZoomRange;
                    container.data("ms1zoomRange", ms1zoomRange);
                }
            }

            createMs1Plot(container);
            setupMs1PlotInteractions(container);
        }

        setupInteractions(container);

        if(options.showIonTable) {
            makeIonTable(container);
        }
    }

    // trim any 0 intensity peaks from the end of the ms/ms peaks array
    function trimPeaksArray(options)
    {
        var peaksLength = options.peaks.length;
        var lastNonZeroIntensityPeakIndex = peaksLength - 1;
        for(var i = peaksLength - 1; i >= 0; i--)
        {
            if(options.peaks[i][1] != 0.0)
            {
                lastNonZeroIntensityPeakIndex = i;
                break;
            }
        }
        if(lastNonZeroIntensityPeakIndex < peaksLength - 1)
        {
            options.peaks.splice(lastNonZeroIntensityPeakIndex+1, peaksLength - lastNonZeroIntensityPeakIndex);
        }
    }

    function storeContainerData(container, options) {
        container.data("index", index);
        container.data("options", options);
        container.data("massErrorChanged", false);
        container.data("massTypeChanged", false);
        container.data("peakAssignmentTypeChanged", false);
        container.data("peakLabelTypeChanged", false);
        container.data("selectedNeutralLossChanged", false);
        container.data("plot", null);           // MS/MS plot
        container.data("ms1plot", null);        // MS1 plot (only created when data is available)
        container.data("zoomRange", null);      // for zooming MS/MS plot
        container.data("ms1zoomRange", null);
        container.data("previousPoint", null);  // for tooltips
        container.data("ionSeries", {a: [], b: [], c: [], x: [], y: [], z: [], mh: []});
        container.data("ionSeriesLabels", {a: [], b: [], c: [], x: [], y: [], z: [], mh: []});
        container.data("ionSeriesMatch", {a: [], b: [], c: [], x: [], y: [], z: [], mh: []});
        container.data("massError", options.massError);
        container.data("internalIons", []);
        container.data("internalIonsMatch", []);
        container.data("internalIonsLabels", []);


        var maxInt = getMaxInt(options);
        var xmin = options.peaks[0][0];
        var xmax = options.peaks[options.peaks.length - 1][0];
        var padding = (xmax - xmin) * 0.025;
        // console.log("x-axis padding: "+padding);
        var plotOptions =  {
                series: {
                    peaks: { show: true, lineWidth: 1, shadowSize: 0},
                    shadowSize: 0
                },
                selection: { mode: "x", color: "#F0E68C" },
                grid: { show: true,
                        hoverable: true,
                        clickable: false,
                        autoHighlight: false,
                        borderWidth: 1,
                        labelMargin: 1},
                xaxis: { tickLength: 3, tickColor: "#000",
                         min: xmin - padding,
                         max: xmax + padding},
                yaxis: { tickLength: 0, tickColor: "#000",
                         max: maxInt*1.1,
                         ticks: [0, maxInt*0.1, maxInt*0.2, maxInt*0.3, maxInt*0.4, maxInt*0.5,
                                 maxInt*0.6, maxInt*0.7, maxInt*0.8, maxInt*0.9, maxInt],
                         tickFormatter: function(val, axis) {return Math.round((val * 100)/maxInt)+"%";}}
	        }
        container.data("plotOptions", plotOptions);
        container.data("maxInt", maxInt);

    }

	function getMaxInt(options) {
		var maxInt = 0;
		for(var j = 0; j < options.peaks.length; j += 1) {
			var peak = options.peaks[j];
			if(peak[1] > maxInt) {
				maxInt = peak[1];
			}
		}
		//alert(maxInt);
		return maxInt;
	}
	
	function round(number) {
		return number.toFixed(4);
	}
	
	function setMassError(container) {
   		var me = parseFloat($(getElementSelector(container, elementIds.massError)).val());
		if(me != container.data("massError")) {
			container.data("massError", me);
			container.data("massErrorChanged", true);
			var options = container.data("options");
			if(options.useCookies) {
				createCookie('lorikeetmasserror', '' + me);
			}
		}
		else {
			container.data("massErrorChanged", false);
		}
   	}

    // -----------------------------------------------
	// CREATE MS1 PLOT
	// -----------------------------------------------
	function createMs1Plot(container) {

        var ms1zoomRange = container.data("ms1zoomRange");
        var options = container.data("options");

		var data = [{data: options.ms1peaks, color: "#bbbbbb", labelType: 'none', hoverable: false, clickable: false}];
		if(options.precursorPeaks) {
			if(options.precursorPeakClickFn)
				data.push({data: options.precursorPeaks, color: "#ff0000", hoverable: true, clickable: true});
			else
				data.push({data: options.precursorPeaks, color: "#ff0000", hoverable: false, clickable: false});
		}
		
		// the MS/MS plot should have been created by now.  This is a hack to get the plots aligned.
		// We will set the y-axis labelWidth to this value.
		var labelWidth = container.data("plot").getAxes().yaxis.labelWidth;
		
		var ms1plotOptions = {
				series: { peaks: {show: true, shadowSize: 0}, shadowSize: 0},
				grid: { show: true, 
						hoverable: true, 
						autoHighlight: true,
						clickable: true,
						borderWidth: 1,
						labelMargin: 1},
				selection: { mode: "xy", color: "#F0E68C" },
		        xaxis: { tickLength: 2, tickColor: "#000" },
		    	yaxis: { tickLength: 0, tickColor: "#fff", ticks: [], labelWidth: labelWidth }
		};
		
		if(ms1zoomRange) {
			ms1plotOptions.xaxis.min = ms1zoomRange.xaxis.from;
			ms1plotOptions.xaxis.max = ms1zoomRange.xaxis.to;
			ms1plotOptions.yaxis.min = 0; // ms1zoomRange.yaxis.from;
			ms1plotOptions.yaxis.max = ms1zoomRange.yaxis.to;
		}

		var placeholder = $(getElementSelector(container, elementIds.msPlot));
		var ms1plot = $.plot(placeholder, data, ms1plotOptions);
        container.data("ms1plot", ms1plot);


		// Mark the precursor peak with a green triangle.
		if(options.precursorMz) {

            var o = ms1plot.pointOffset({ x: options.precursorMz, y: options.precursorIntensity});
            var ctx = ms1plot.getCanvas().getContext("2d");
            ctx.beginPath();
            ctx.moveTo(o.left-10, o.top-5);
            ctx.lineTo(o.left-10, o.top + 5);
            ctx.lineTo(o.left-10 + 10, o.top);
            ctx.lineTo(o.left-10, o.top-5);
            ctx.fillStyle = "#008800";
            ctx.fill();
            placeholder.append('<div style="position:absolute;left:' + (o.left + 4) + 'px;top:' + (o.top-4) + 'px;color:#000;font-size:smaller">'+options.precursorMz.toFixed(2)+'</div>');

		}
		
		// mark the scan number if we have it
		o = ms1plot.getPlotOffset();
		if(options.ms1scanLabel) {
			placeholder.append('<div style="position:absolute;left:' + (o.left + 4) + 'px;top:' + (o.top+4) + 'px;color:#666;font-size:smaller">MS1 scan: '+options.ms1scanLabel+'</div>');
		}
		
		// zoom out icon on plot right hand corner if we are not already zoomed in to the precursor.
		if(container.data("ms1zoomRange")) {
			placeholder.append('<div id="'+getElementId(container, elementIds.ms1plot_zoom_out)+'" class="zoom_out_link"  style="position:absolute; left:'
					+ (o.left + ms1plot.width() - 40) + 'px;top:' + (o.top+4) + 'px;"></div>');

			$(getElementSelector(container, elementIds.ms1plot_zoom_out)).click( function() {
				container.data("ms1zoomRange", null);
				createMs1Plot(container);
			});
		}
		else {
			placeholder.append('<div id="'+getElementId(container, elementIds.ms1plot_zoom_in)+'" class="zoom_in_link"  style="position:absolute; left:'
					+ (o.left + ms1plot.width() - 20) + 'px;top:' + (o.top+4) + 'px;"></div>');
			$(getElementSelector(container, elementIds.ms1plot_zoom_in)).click( function() {
				var ranges = {};
				ranges.yaxis = {};
				ranges.xaxis = {};
				ranges.yaxis.from = 0.0;
				ranges.yaxis.to = options.maxIntensityInMs1ZoomRange;

                ranges.xaxis.from = options.precursorMz - 5.0;
                ranges.xaxis.to = options.precursorMz + 5.0;

                container.data("ms1zoomRange", ranges);
				createMs1Plot(container);
			});
		}
	}

    // -----------------------------------------------
	// SET UP INTERACTIVE ACTIONS FOR MS1 PLOT
	// -----------------------------------------------
	function setupMs1PlotInteractions(container) {
		
		var placeholder = $(getElementSelector(container, elementIds.msPlot));
        var options = container.data("options");

		// allow clicking on plot if we have a function to handle the click
		if(options.precursorPeakClickFn != null) {
			placeholder.bind("plotclick", function (event, pos, item) {
				
		        if (item) {
		          //highlight(item.series, item.datapoint);
		        	options.precursorPeakClickFn(item.datapoint[0]);
		        }
		    });
		}
		
		// allow zooming the plot
		placeholder.bind("plotselected", function (event, ranges) {
            container.data("ms1zoomRange", ranges);
			createMs1Plot(container);
	    });
		
	}

    // -----------------------------------------------
	// CREATE MS/MS PLOT
	// -----------------------------------------------
	function createPlot(container, datasets) {

        var plot;
    	if(!container.data("zoomRange")) {
    		plot = $.plot($(getElementSelector(container, elementIds.msmsplot)), datasets,  container.data("plotOptions"));
        }
    	else {
            var zoomRange = container.data("zoomRange");
            var selectOpts = {};
    		if($(getElementSelector(container, elementIds.zoom_x)).is(":checked"))
    			selectOpts.xaxis = { min: zoomRange.xaxis.from, max: zoomRange.xaxis.to };
    		if($(getElementSelector(container, elementIds.zoom_y)).is(":checked"))
    			selectOpts.yaxis = { min: 0, max: zoomRange.yaxis.to };
    		
    		plot = $.plot(getElementSelector(container, elementIds.msmsplot), datasets,
                      $.extend(true, {}, container.data("plotOptions"), selectOpts));

    		// zoom out icon on plot right hand corner
    		var o = plot.getPlotOffset();
    		$(getElementSelector(container, elementIds.msmsplot)).append('<div id="'+getElementId(container, elementIds.ms2plot_zoom_out)+'" class="zoom_out_link" style="position:absolute; left:'
					+ (o.left + plot.width() - 20) + 'px;top:' + (o.top+4) + 'px"></div>');

			$(getElementSelector(container, elementIds.ms2plot_zoom_out)).click( function() {
                resetZoom(container);
			});
    	}
    	// we have re-calculated and re-drawn everything..
    	container.data("massTypeChanged", false);
    	container.data("massErrorChanged",false);
    	container.data("peakAssignmentTypeChanged", false);
    	container.data("peakLabelTypeChanged", false);
    	container.data("selectedNeutralLossChanged", false);
        container.data("plot", plot);
    }
	
	// -----------------------------------------------
	// SET UP INTERACTIVE ACTIONS FOR MS/MS PLOT
	// -----------------------------------------------
	function setupInteractions (container) {

		// ZOOMING
	    $(getElementSelector(container, elementIds.msmsplot)).bind("plotselected", function (event, ranges) {
	    	container.data("zoomRange", ranges);
	    	createPlot(container, getDatasets(container));
	    });
	    
	    // ZOOM AXES
	    $(getElementSelector(container, elementIds.zoom_x)).click(function() {
	    	resetAxisZoom(container);
	    });
	    $(getElementSelector(container, elementIds.zoom_y)).click(function() {
	    	resetAxisZoom(container);
	    });
	    
		// RESET ZOOM
		$(getElementSelector(container, elementIds.resetZoom)).click(function() {
			resetZoom(container);
	   	});
		
		// UPDATE
		$(getElementSelector(container, elementIds.update)).click(function() {
			container.data("zoomRange", null); // zoom out fully
			setMassError(container);
			createPlot(container, getDatasets(container));
			makeIonTable(container);
	   	});
		
		// TOOLTIPS
		$(getElementSelector(container, elementIds.msmsplot)).bind("plothover", function (event, pos, item) {

	        if($(getElementSelector(container, elementIds.enableTooltip)+":checked").length > 0) {
	            if (item) {
	                if (container.data("previousPoint") != item.datapoint) {
	                    container.data("previousPoint", item.datapoint);
	                    
	                    $(getElementSelector(container, elementIds.msmstooltip)).remove();
	                    var x = item.datapoint[0].toFixed(2),
	                        y = item.datapoint[1].toFixed(2);
	                    
	                    showTooltip(container, item.pageX, item.pageY,
	                                "m/z: " + x + "<br>intensity: " + y);
	                }
	            }
	            else {
	                $(getElementSelector(container, elementIds.msmstooltip)).remove();
	                container.data("previousPoint", null);
	            }
	        }
	    });
		$(getElementSelector(container, elementIds.enableTooltip)).click(function() {
			$(getElementSelector(container, elementIds.msmstooltip)).remove();
		});
		
		// SHOW / HIDE ION SERIES; UPDATE ON MASS TYPE CHANGE; 
		// PEAK ASSIGNMENT TYPE CHANGED; PEAK LABEL TYPE CHANGED
		var ionChoiceContainer = $(getElementSelector(container, elementIds.ion_choice));
		ionChoiceContainer.find("input").click(function() {
            plotAccordingToChoices(container)
        });
		
		var neutralLossContainer = $(getElementSelector(container, elementIds.nl_choice));
		neutralLossContainer.find("input").click(function() {
			container.data("selectedNeutralLossChanged", true);
			plotAccordingToChoices(container);
		});
		
	    container.find("input[name='"+getRadioName(container, "massTypeOpt")+"']").click(function() {
	    	container.data("massTypeChanged", true);
	    	plotAccordingToChoices(container);
	    });
        $(getElementSelector(container, elementIds.peakDetect)).click(function() {
            container.data("peakAssignmentTypeChanged", true);
            plotAccordingToChoices(container);
        });

	    container.find("input[name='"+getRadioName(container, "peakAssignOpt")+"']").click(function() {
	    	container.data("peakAssignmentTypeChanged", true);
	    	plotAccordingToChoices(container);
	    });

        $(getElementSelector(container, elementIds.deselectIonsLink)).click(function() {
			ionChoiceContainer.find("input:checkbox:checked").each(function() {
				$(this).attr('checked', "");
			});
			
			plotAccordingToChoices(container);
		});

	    container.find("input[name='"+getRadioName(container, "peakLabelOpt")+"']").click(function() {
	    	container.data("peakLabelTypeChanged", true);
	    	plotAccordingToChoices(container);
	    });

	    
	    
	    // MOVING THE ION TABLE
	    makeIonTableMovable(container);
	    
	    // CHANGING THE PLOT SIZE
	    makePlotResizable(container);
	    
	    // PRINT SPECTRUM
	    printPlot(container);
		
	}
	
	function resetZoom(container) {
		container.data("zoomRange", null);
		setMassError(container);
		createPlot(container, getDatasets(container));
	}
		
	function savePlotCookies(container) {
		var options = container.data('options');
		if(options.useCookies) {
        var ionChoiceContainer = $(getElementSelector(container, elementIds.ion_choice));
        ionChoiceContainer.find("input").each(function() {
                var checked = $(this).is(":checked");
                var id = $(this).attr("id");
                createCookie("lorikeet"+id, checked);
        });
		}		
	}
	
	function loadPlotCookies(container) {
		var options = container.data('options');
		if(options.useCookies) {
        var ionChoiceContainer = $(getElementSelector(container, elementIds.ion_choice));
        ionChoiceContainer.find("input").each(function() {
                var checked = $(this).is(":checked");
                var id = $(this).attr("id");
                var value = readCookie("lorikeet"+id);
                if(value) {
                	if(value == "true") {
                		$(this).attr("checked", true);
                	} else if(value == "false") {
                		$(this).attr("checked", false);
                	}
                }
        });
		}				
	}
	
	function plotAccordingToChoices(container) {
		savePlotCookies(container);
        var data = getDatasets(container);

		if (data.length > 0) {
            createPlot(container, data);
            makeIonTable(container);
            showSequenceInfo(container); // update the MH+ and m/z values
        }
    }
	
	function resetAxisZoom(container) {

        var plot = container.data("plot");
        var plotOptions = container.data("plotOptions");

    	var zoom_x = false;
		var zoom_y = false;
		if($(getElementSelector(container, elementIds.zoom_x)).is(":checked"))
			zoom_x = true;
		if($(getElementSelector(container, elementIds.zoom_y)).is(":checked"))
			zoom_y = true;
    	if(zoom_x && zoom_y) {
    		plotOptions.selection.mode = "xy";
			if(plot) plot.getOptions().selection.mode = "xy";
    	}
		else if(zoom_x) {
			plotOptions.selection.mode = "x";
			if(plot) plot.getOptions().selection.mode = "x";
		}
		else if(zoom_y) {
			plotOptions.selection.mode = "y";
			if(plot) plot.getOptions().selection.mode = "y";
		}
	}
	
	function showTooltip(container, x, y, contents) {
        $('<div id="'+getElementId(container, elementIds.msmstooltip)+'">' + contents + '</div>').css( {
            position: 'absolute',
            display: 'none',
            top: y + 5,
            left: x + 5,
            border: '1px solid #fdd',
            padding: '2px',
            'background-color': '#F0E68C',
            opacity: 0.80
        }).appendTo("body").fadeIn(200);
    }
	
	function makePlotResizable(container) {

        var options = container.data("options");

		$(getElementSelector(container, elementIds.slider_width)).slider({
			value:options.width,
			min: 100,
			max: 1500,
			step: 50,
			slide: function(event, ui) {
				var width = ui.value;
				//console.log(ui.value);
				options.width = width;
				$(getElementSelector(container, elementIds.msmsplot)).css({width: width});
				plotAccordingToChoices(container);
				if(options.ms1peaks && options.ms1peaks.length > 0) {
					$(getElementSelector(container, elementIds.msPlot)).css({width: width});
					createMs1Plot(container);
				}
				$(getElementSelector(container, elementIds.slider_width_val)).text(width);
			}
		});
		
		$(getElementSelector(container, elementIds.slider_height)).slider({
			value:options.height,
			min: 100,
			max: 1000,
			step: 50,
			slide: function(event, ui) {
				var height = ui.value;
				//console.log(ui.value);
				options.height = height
				$(getElementSelector(container, elementIds.msmsplot)).css({height: height});
				plotAccordingToChoices(container);
				$(getElementSelector(container, elementIds.slider_height_val)).text(height);
			}
		});
	}
	
	function printPlot(container) {

		$(getElementSelector(container, elementIds.printLink)).click(function() {

            var parent = container.parent();

			// create another div and move the plots into that div
			$(document.body).append('<div id="tempPrintDiv"></div>');
			$("#tempPrintDiv").append(container.detach());
			$("#tempPrintDiv").siblings().addClass("noprint");
			
			var plotOptions = container.data("plotOptions");

			container.find(".bar").addClass('noprint');
			$(getElementSelector(container, elementIds.optionsTable)).addClass('noprint');
			$(getElementSelector(container, elementIds.ionTableLoc1)).addClass('noprint');
			$(getElementSelector(container, elementIds.ionTableLoc2)).addClass('noprint');
			$(getElementSelector(container, elementIds.viewOptionsDiv)).addClass('noprint');
			
			plotOptions.series.peaks.print = true; // draw the labels in the DOM for sharper print output
			plotAccordingToChoices(container);
			window.print();
			
			
			// remove the class after printing so that if the user prints 
			// via the browser's print menu the whole page is printed
			container.find(".bar").removeClass('noprint');
			$(getElementSelector(container, elementIds.optionsTable)).removeClass('noprint');
			$(getElementSelector(container, elementIds.ionTableLoc1)).removeClass('noprint');
			$(getElementSelector(container, elementIds.ionTableLoc2)).removeClass('noprint');
			$(getElementSelector(container, elementIds.viewOptionsDiv)).removeClass('noprint');
			$("#tempPrintDiv").siblings().removeClass("noprint");
			


			plotOptions.series.peaks.print = false; // draw the labels in the canvas
			plotAccordingToChoices(container);
			
			// move the plots back to the original location
            parent.append(container.detach());
			$("#tempPrintDiv").remove();
			
			
			/*var canvas = plot.getCanvas();
			var iWidth=3500;
			var iHeight = 3050;
			var oSaveCanvas = document.createElement("canvas");
			oSaveCanvas.width = iWidth;
			oSaveCanvas.height = iHeight;
			oSaveCanvas.style.width = iWidth+"px";
			oSaveCanvas.style.height = iHeight+"px";
			var oSaveCtx = oSaveCanvas.getContext("2d");
			oSaveCtx.drawImage(canvas, 0, 0, canvas.width, canvas.height, 0, 0, iWidth, iHeight);
			
			var dataURL = oSaveCanvas.toDataURL("image/png");
			window.location = dataURL;*/
			
			
		});
	}
	
	// -----------------------------------------------
	// SELECTED DATASETS
	// -----------------------------------------------
	function getDatasets(container) {

        var options = container.data("options");

		 // selected ions
		var selectedIonTypes = getSelectedIonTypes(container);
		
		calculateTheoreticalSeries(container, selectedIonTypes);
		
		// add the un-annotated peaks
		var data = [{data: options.peaks, color: "#bbbbbb", labelType: 'none'}];
		
		// add the annotated peaks
		var seriesMatches = getSeriesMatches(container, selectedIonTypes);
		for(var i = 0; i < seriesMatches.length; i += 1) {
			data.push(seriesMatches[i]);
		}
		
		// add any user specified extra peaks
		for(var i = 0; i < options.extraPeakSeries.length; i += 1) {
			data.push(options.extraPeakSeries[i]);
		}
		return data;
	}
	
	//-----------------------------------------------
	// SELECTED ION TYPES
	// -----------------------------------------------
	function getSelectedIonTypes(container) {

		var ions = [];
		var charges = [];
		$(getElementSelector(container, elementIds.ion_choice)).find("input:checked").each(function () {
	        var key = $(this).attr("id");
	        var tokens = key.split("_");
            if(tokens.length < 2)
                return;
	        ions.push(tokens[0]);
	        charges.push(tokens[1]);
	  	});
	    
	    var selected = [];
        var ion;
        for (var i = 0; i < ions.length; i += 1) {
            selected.push(ion = Ion.get(ions[i], charges[i]));
        }
	    
	    return selected;
	}

    function internalIonsEnabled(container) {
        return $(getElementSelector(container, elementIds.ion_choice)).find("#internal").attr("checked");
    }

    function allIonsEnabled(container) {
        var options = container.data("options");
        return options.showAllTable;
    }    

    function getAllIons(container) {
        var options = container.data("options");

        // selected ions
        var selectedIonTypes = getSelectedIonTypes(container);
        var ntermIons = getSelectedNtermIons(selectedIonTypes);
        var ctermIons = getSelectedCtermIons(selectedIonTypes);
        var ionSeries = container.data("ionSeries");

        var allIons = [];

        for(var i = 0; i < selectedIonTypes.length; i += 1) {
            var selectedIon = selectedIonTypes[i];
            if(selectedIon.term == null) {
                var neutralLosses = getNeutralLosses(container);
                for(var nl = 0; nl < neutralLosses.length; nl += 1) {
                    var neutralLoss = neutralLosses[nl];
                    var seriesData = getCalculatedSeries(ionSeries, selectedIon);
                    var sion = seriesData[0];
		    if(!neutralLoss.applies(sion)) {
			continue;
		    }
                    var ionLabel = matchLabel(sion, neutralLoss.label);
                    var ionmz = ionMz(sion, neutralLoss.label);
                    allIons.push({"mz": ionmz, "label": ionLabel, matched: false});
                }
            }
        }

        for(var i = 0; i < options.sequence.length; i += 1) {
            var aaChar = options.sequence.charAt(i);

            // nterm ions
            for(var n = 0; n < ntermIons.length; n += 1) {
                if(i < options.sequence.length - 1) {
                    var seriesData = getCalculatedSeries(ionSeries, ntermIons[n]);
                    var neutralLosses = getNeutralLosses(container);
                    var sion = seriesData[i];
			for(var nl = 0; nl < neutralLosses.length; nl += 1) {
				var neutralLoss = neutralLosses[nl];
				if(!neutralLoss.applies(sion)) {
					continue;
				}
				var ionLabel = matchLabel(sion, neutralLoss.label);
				var ionmz = ionMz(sion, neutralLoss.label);
				allIons.push({"mz": ionmz, "label": ionLabel, matched: false});
	                }
		}
            }
            
            for(var c = 0; c < ctermIons.length; c += 1) {
                if(i > 0) {
                    var seriesData = getCalculatedSeries(ionSeries, ctermIons[c]);
                    var idx = options.sequence.length - i - 1;
                    var neutralLosses = getNeutralLosses(container);
                    var sion = seriesData[idx];
													for(var nl = 0; nl < neutralLosses.length; nl += 1) {
													     var neutralLoss = neutralLosses[nl];
				if(!neutralLoss.applies(sion)) {
					continue;
				}

																 var ionLabel = matchLabel(sion, neutralLoss.label);
																 var ionmz = ionMz(sion, neutralLoss.label);
																 allIons.push({"mz": ionmz, "label": ionLabel, matched: false});
                    }
                } 
            }
        }

        if(internalIonsEnabled(container)) {
            var internalIons = container.data("internalIons");
            for(var i = 0; i < internalIons.length; i += 1) {
                var sion = internalIons[i];
                var neutralLosses = getNeutralLosses(container);
                for(var nl = 0; nl < neutralLosses.length; nl += 1) {
                    var neutralLoss = neutralLosses[nl];
                    if(!neutralLoss.applies(sion)) {
                        continue;
                    }
                    var ionLabel = matchLabel(sion, neutralLoss.label);
                    var ionmz = ionMz(sion, neutralLoss.label);
                    allIons.push({"mz": ionmz, "label": ionLabel, matched: false});
                }
            }
        }
        sortByMz(allIons);
        return allIons;
    }

    function makeAllIonsTable(container) {
        var numColumns = 4; 
        var myTable = "";
        myTable += '<table id="' + getElementId(container, elementIds.allTableLoc) + '" cellpadding="2" class="font_small '+elementIds.ionTable+ '" style="margin-top:5px;">';
        myTable +=  "<thead>" ;
        myTable +=   "<tr>";
        for(colNum = 0; colNum < numColumns; colNum++) {
             myTable +=    "<th>" +"Ion"+ "</th>"; 
             myTable +=    "<th>" +"&nbsp;"+ "</th>";
        } 
        myTable +=   "</tr>";
        myTable +=  "</thead>";

        var allIons = getAllIons(container);
        for(var i = 0; i < allIons.length; i++) {
            if(i % numColumns == 0) { // Start, end row.
                 if(i > 0) {
                      myTable += "</tr>";
                 }
                 myTable += "<tr>";
            }
            var ion = allIons[i];
            // Encode for HTML
            var label = $('<div/>').text(ion["label"]).html();
            var mz = ion["mz"];
            var cls = "";
            var style="";
            // Don't enable this until we can determine in main series ions are enabled.
            /*
            if(ion.match) {
                cls="matchIon";
                style="style='background-color:"+INTERNAL_ION_COLOR+";'";
            }
            */
            myTable += "<td class='seq'>" + label + "</td><td class='" + cls +"' " + style + " >" + round(mz) + "</td>";
        }
        myTable += "</tr>";
        myTable += "</table>"
        return myTable;
    }
 

    function makeInternalIonsTable(container) {
        var myTable = "";
        myTable += '<table id="'+getElementId(container, elementIds.internalIonTable)+'" cellpadding="2" class="font_small '+elementIds.ionTable+ '" style="margin-top:5px;">' ;
        myTable +=  "<thead>" ;
        myTable +=   "<tr>";
        myTable +=    "<th>" +"Seq"+ "</th>"; 
        myTable +=    "<th>" +"&nbsp;"+ "</th>"; 
        myTable +=   "</tr>";
        myTable +=  "</thead>";

        var internalIons = container.data("internalIons");
        for(var i = 0; i < internalIons.length; i++) {
            var internalIon = internalIons[i];
            var label = internalIon["sequence"];
            var mz = internalIon["mz"];
            var cls = "";
            var style="";
            if(internalIon.match) {
                cls="matchIon";
                style="style='background-color:"+INTERNAL_ION_COLOR+";'";
            }
            myTable += "<tr><td class='seq'>" + label + "</td><td class='" + cls +"' " + style + " >" + round(mz) + "</td></tr>";
        }

        myTable += "</table>"
        return myTable;
    }
	
	function getSelectedNtermIons(selectedIonTypes) {
		var ntermIons = [];
		
		for(var i = 0; i < selectedIonTypes.length; i += 1) {
			var sion = selectedIonTypes[i];
			if(sion.type == "a" || sion.type == "b" || sion.type == "c") 
				ntermIons.push(sion);
		}
		ntermIons.sort(function(m,n) {
			if(m.type == n.type) {
				return (m.charge - n.charge);
			}
			else {
				return m.type - n.type;
			}
		});
		return ntermIons;
	}

	function getSelectedCtermIons(selectedIonTypes) {
		var ctermIons = [];
		
		for(var i = 0; i < selectedIonTypes.length; i += 1) {
			var sion = selectedIonTypes[i];
			if(sion.type == "x" || sion.type == "y" || sion.type == "z") 
				ctermIons.push(sion);
		}
		ctermIons.sort(function(m,n) {
			if(m.type == n.type) {
				return (m.charge - n.charge);
			}
			else {
				return m.type - n.type;
			}
		});
		return ctermIons;
	}
	
	// ---------------------------------------------------------
	// CALCUALTE THEORETICAL MASSES FOR THE SELECTED ION SERIES
	// ---------------------------------------------------------
	function calculateTheoreticalSeries(container, selectedIons) {

		if(selectedIons) {
		
			var todoIonSeries = [];
			var todoIonSeriesData = [];
            var ionSeries = container.data("ionSeries");
			for(var i = 0; i < selectedIons.length; i += 1) {
				var sion = selectedIons[i];
				if(sion.type == "a") {
					if(!container.data("massTypeChanged") && ionSeries.a[sion.charge])	continue; // already calculated
					else {
						todoIonSeries.push(sion);
						ionSeries.a[sion.charge] = [];
						todoIonSeriesData.push(ionSeries.a[sion.charge]);
					}
				}
				if(sion.type == "b") {
					if(!container.data("massTypeChanged") && ionSeries.b[sion.charge])	continue; // already calculated
					else {
						todoIonSeries.push(sion);
						ionSeries.b[sion.charge] = [];
						todoIonSeriesData.push(ionSeries.b[sion.charge]);
					}
				}
				if(sion.type == "c") {
					if(!container.data("massTypeChanged") && ionSeries.c[sion.charge])	continue; // already calculated
					else {
						todoIonSeries.push(sion);
						ionSeries.c[sion.charge] = [];
						todoIonSeriesData.push(ionSeries.c[sion.charge]);
					}
				}
				if(sion.type == "x") {
					if(!container.data("massTypeChanged") && ionSeries.x[sion.charge])	continue; // already calculated
					else {
						todoIonSeries.push(sion);
						ionSeries.x[sion.charge] = [];
						todoIonSeriesData.push(ionSeries.x[sion.charge]);
					}
				}
				if(sion.type == "y") {
					if(!container.data("massTypeChanged") && ionSeries.y[sion.charge])	continue; // already calculated
					else {
						todoIonSeries.push(sion);
						ionSeries.y[sion.charge] = [];
						todoIonSeriesData.push(ionSeries.y[sion.charge]);
					}
				}
				if(sion.type == "z") {
					if(!container.data("massTypeChanged") && ionSeries.z[sion.charge])	continue; // already calculated
					else {
						todoIonSeries.push(sion);
						ionSeries.z[sion.charge] = [];
						todoIonSeriesData.push(ionSeries.z[sion.charge]);
					}
				}
                if(sion.type == "mh") {
                    if(!container.data("massTypeChanged") && ionSeries.mh[sion.charge])  continue; // already calculated
                    else {
                        todoIonSeries.push(sion);
                        ionSeries.mh[sion.charge] = [];
                        todoIonSeriesData.push(ionSeries.mh[sion.charge]);
                    }
                }                
			}

			if(container.data("options").sequence) {

                var sequence =  container.data("options").sequence
				var massType = container.find("input[name='"+getRadioName(container, "massTypeOpt")+"']:checked").val();
				
				for(var i = 1; i < sequence.length; i += 1) {
					
					for(var j = 0; j < todoIonSeries.length; j += 1) {
						var tion = todoIonSeries[j];
						var ionSeriesData = todoIonSeriesData[j];
						if(tion.term == "n")
							ionSeriesData.push(sion = Ion.getSeriesIon(tion, container.data("options").peptide, i, massType));
						else if(tion.term == "c")
							ionSeriesData.unshift(sion = Ion.getSeriesIon(tion, container.data("options").peptide, i, massType));
					}
				}

                // Add whole sequence ions
                for(var j = 0; j < todoIonSeries.length; j += 1) {
                    var tion = todoIonSeries[j];
                    var ionSeriesData = todoIonSeriesData[j];
                    if(tion.term == null) {
                        ionSeriesData.push(sion = Ion.getSeriesIon(tion, container.data("options").peptide, null, massType));                        
                    }
                }                

                if(internalIonsEnabled(container)) {
                    var internalIons = getInternalIons(container.data("options").peptide, massType);
                    container.data("internalIons", internalIons);
                }
			}
		}
	}

	
	// -----------------------------------------------
	// MATCH THEORETICAL MASSES WITH PEAKS IN THE SCAN
	// -----------------------------------------------
	function recalculate(container) {
        return (container.data("massErrorChanged") ||
				container.data("massTypeChanged") ||
				container.data("peakAssignmentTypeChanged") ||
				container.data("selectedNeutralLossChanged"));
	}

	function getSeriesMatches(container, selectedIonTypes) {
		
		var dataSeries = [];
		
		var peakAssignmentType = container.find("input[name='"+getRadioName(container, "peakAssignOpt")+"']:checked").val();
		var peakLabelType = container.find("input[name='"+getRadioName(container, "peakLabelOpt")+"']:checked").val();

        var ionSeriesMatch = container.data("ionSeriesMatch");
        var ionSeries = container.data("ionSeries");
        var ionSeriesLabels = container.data("ionSeriesLabels");
        var options = container.data("options");
        var massError = container.data("massError");
        var peaks = getPeaks(container);

		for(var j = 0; j < selectedIonTypes.length; j += 1) {
		
			var ion = selectedIonTypes[j];
							
			
			if(ion.type == "a") {
				if(recalculate(container) || !ionSeriesMatch.a[ion.charge]) { // re-calculate only if mass error has changed OR
																		// matching peaks for this series have not been calculated
					// calculated matching peaks
					var adata = calculateMatchingPeaks(container, ionSeries.a[ion.charge], peaks, massError, peakAssignmentType);
					if(adata && adata.length > 0) {
						ionSeriesMatch.a[ion.charge] = adata[0];
						ionSeriesLabels.a[ion.charge] = adata[1];
					}
				}
				dataSeries.push({data: ionSeriesMatch.a[ion.charge], color: ion.color, labelType: peakLabelType, labels: ionSeriesLabels.a[ion.charge]});
			}
			
			if(ion.type == "b") {
				if(recalculate(container) || !ionSeriesMatch.b[ion.charge]) { // re-calculate only if mass error has changed OR
																		// matching peaks for this series have not been calculated
					// calculated matching peaks
					var bdata = calculateMatchingPeaks(container, ionSeries.b[ion.charge], peaks, massError, peakAssignmentType);
					if(bdata && bdata.length > 0) {
						ionSeriesMatch.b[ion.charge] = bdata[0];
						ionSeriesLabels.b[ion.charge] = bdata[1];
					}
				}
				dataSeries.push({data: ionSeriesMatch.b[ion.charge], color: ion.color, labelType: peakLabelType, labels: ionSeriesLabels.b[ion.charge]});
			}
			
			if(ion.type == "c") {
				if(recalculate(container) || !ionSeriesMatch.c[ion.charge]) { // re-calculate only if mass error has changed OR
																		// matching peaks for this series have not been calculated
					// calculated matching peaks
					var cdata = calculateMatchingPeaks(container, ionSeries.c[ion.charge], peaks, massError, peakAssignmentType);
					if(cdata && cdata.length > 0) {
						ionSeriesMatch.c[ion.charge] = cdata[0];
						ionSeriesLabels.c[ion.charge] = cdata[1];
					}
				}
				dataSeries.push({data: ionSeriesMatch.c[ion.charge], color: ion.color, labelType: peakLabelType, labels: ionSeriesLabels.c[ion.charge]});
			}
			
			if(ion.type == "x") {
				if(recalculate(container) || !ionSeriesMatch.x[ion.charge]) { // re-calculate only if mass error has changed OR
																		// matching peaks for this series have not been calculated
					// calculated matching peaks
					var xdata = calculateMatchingPeaks(container, ionSeries.x[ion.charge], peaks, massError, peakAssignmentType);
					if(xdata && xdata.length > 0) {
						ionSeriesMatch.x[ion.charge] = xdata[0];
						ionSeriesLabels.x[ion.charge] = xdata[1];
					}
				}
				dataSeries.push({data: ionSeriesMatch.x[ion.charge], color: ion.color, labelType: peakLabelType, labels: ionSeriesLabels.x[ion.charge]});
			}
			
			if(ion.type == "y") {
				if(recalculate(container) || !ionSeriesMatch.y[ion.charge]) { // re-calculate only if mass error has changed OR
																		// matching peaks for this series have not been calculated
					// calculated matching peaks
					var ydata = calculateMatchingPeaks(container, ionSeries.y[ion.charge], peaks, massError, peakAssignmentType);
					if(ydata && ydata.length > 0) {
						ionSeriesMatch.y[ion.charge] = ydata[0];
						ionSeriesLabels.y[ion.charge] = ydata[1];
					}
				}
				dataSeries.push({data: ionSeriesMatch.y[ion.charge], color: ion.color, labelType: peakLabelType, labels: ionSeriesLabels.y[ion.charge]});
			}
			
			if(ion.type == "z") {
				if(recalculate(container) || !ionSeriesMatch.z[ion.charge]) { // re-calculate only if mass error has changed OR
																		// matching peaks for this series have not been calculated
					// calculated matching peaks
					var zdata = calculateMatchingPeaks(container, ionSeries.z[ion.charge], peaks, massError, peakAssignmentType);
					if(zdata && zdata.length > 0) {
						ionSeriesMatch.z[ion.charge] = zdata[0];
						ionSeriesLabels.z[ion.charge] = zdata[1];
					}
				}
				dataSeries.push({data: ionSeriesMatch.z[ion.charge], color: ion.color, labelType: peakLabelType, labels: ionSeriesLabels.z[ion.charge]});
			}

            if(ion.type == "mh") {
                if(recalculate(container) || !ionSeriesMatch.mh[ion.charge]) { // re-calculate only if mass error has changed OR
                                                                        // matching peaks for this series have not been calculated
                    // calculated matching peaks
                    var mhdata = calculateMatchingPeaks(container, ionSeries.mh[ion.charge], peaks, massError, peakAssignmentType);
                    if(mhdata && mhdata.length > 0) {
                        ionSeriesMatch.mh[ion.charge] = mhdata[0];
                        ionSeriesLabels.mh[ion.charge] = mhdata[1];
                    }
                }
                dataSeries.push({data: ionSeriesMatch.mh[ion.charge], color: ion.color, labelType: peakLabelType, labels: ionSeriesLabels.mh[ion.charge]});
            }
		}

        if(internalIonsEnabled(container)) {
            var internalIonsMatch = container.data("internalIonsMatch");
            var internalIonsLabels = container.data("internalIonsLabels");
            
            if(recalculate(container) || (internalIonsMatch.length == 0)) { // TODO replace true with actual check mimicing above
                var internalIons = container.data("internalIons");
                var internalIonsMatch = container.data("internalIonsMatch");

                // TODO: Keep working on this.
                for(var i = 0; i < internalIons.length; i += 1) {
                    var sion = internalIons[i];
                    var peakIndex = 0;
        
                    var matchData = [];
                    matchData[0] = []; // peaks
                    matchData[1] = []; // labels -- ions;
                    var neutralLosses = getNeutralLosses(container);
                    for(var n = 0; n < neutralLosses.length; n += 1) {
                        var neutralLoss = neutralLosses[n];
                        if(!neutralLoss.applies(sion)) {
                            continue;
                        }

                        peakIndex = getMatchForIon(sion, matchData, peaks, peakIndex, massError, peakAssignmentType, neutralLoss);

                        if(matchData && matchData.length > 0) {
                            internalIonsMatch[sion.label] = matchData[0];
                            internalIonsLabels[sion.label] = matchData[1];
                            dataSeries.push({data: internalIonsMatch[sion.label], color: INTERNAL_ION_COLOR, labelType: peakLabelType, labels: internalIonsLabels[sion.label]});
                        }
                    }
                }
            }
        }

		return dataSeries;
	}

		function getNeutralLosses(container) {
			var options = container.data("options");
			var neutralLosses = [];
			$(getElementSelector(container, elementIds.nl_choice)).find("input:checked").each(function() {
				neutralLosses.push(NeutralLoss.get($(this).val(), options.residueSpecificNeutralLosses));
			});
			neutralLosses.push(NeutralLoss.get(null)); // Always calculate base ions without neutral loss applied.
			return neutralLosses;
		}

		function matchLabel(sion, neutralLoss) {
			var label = sion.label;
			if(neutralLoss) {
				if(neutralLoss == 'h2o') {
					label += 'o';
				}
				else if(neutralLoss = 'nh3') {
					label += '*';
				}
			}
			return label;
		}

		function ionMz(sion, neutralLoss) {
			var ionmz;
			if(!neutralLoss)
				ionmz = sion.mz;
			else {
				if(neutralLoss == 'h2o') {
					ionmz = Ion.getWaterLossMz(sion);
				}
				else if(neutralLoss = 'nh3') {
					ionmz = Ion.getAmmoniaLossMz(sion);
				}
			}
			return ionmz;
		}


	function calculateMatchingPeaks(container, ionSeries, allPeaks, massTolerance, peakAssignmentType) {

        // console.log("calculating matching peaks");
		var peakIndex = 0;
		
		var matchData = [];
		matchData[0] = []; // peaks
		matchData[1] = []; // labels -- ions;
		
		var neutralLosses = getNeutralLosses(container);
		for(var i = 0; i < ionSeries.length; i += 1) {
			
			var sion = ionSeries[i];
			
			// get match for water and or ammonia loss
			for(var n = 0; n < neutralLosses.length; n += 1) {
				var neutralLoss = neutralLosses[n];
				if(!neutralLoss.applies(sion)) {
					continue;
				}
				var index = getMatchForIon(sion, matchData, allPeaks, peakIndex, massTolerance, peakAssignmentType, neutralLoss.label);
				if(neutralLosses[n] == null) {
					peakIndex = index;
				}
			}
		}
		
		return matchData;
	}
	
	// sion -- theoretical ion
	// matchData -- array to which we will add a peak if there is a match
	// allPeaks -- array with all the scan peaks
	// peakIndex -- current index in peaks array
	// Returns the index of the matching peak, if one is found
	function getMatchForIon(sion, matchData, allPeaks, peakIndex, massTolerance, peakAssignmentType, neutralLoss) {
		
		var bestPeak = null;
		if(!neutralLoss)
			sion.match = false; // reset;
		var ionmz = ionMz(sion, neutralLoss);
		var bestDistance;
		
		for(var j = peakIndex; j < allPeaks.length; j += 1) {
			 
			var peak = allPeaks[j];
			
			// peak is before the current ion we are looking at
			if(peak[0] < ionmz - massTolerance)
				continue;
				
			// peak is beyond the current ion we are looking at
			if(peak[0] > ionmz + massTolerance) {
			
				// if we found a matching peak for the current ion, save it
				if(bestPeak) {
					//console.log("found match "+sion.label+", "+ionmz+";  peak: "+bestPeak[0]);
					matchData[0].push([bestPeak[0], bestPeak[1]]);
					matchData[1].push(matchLabel(sion, neutralLoss));
					if(!neutralLoss) {
						sion.match = true;
					}
				}
				peakIndex = j;
				break;
			}
				
			// peak is within +/- massTolerance of the current ion we are looking at
			
			// if this is the first peak in the range
			if(!bestPeak) {
				//console.log("found a peak in range, "+peak.mz);
				bestPeak = peak;
				bestDistance = Math.abs(ionmz - peak[0]);
				continue;
			}
			
			// if peak assignment method is Most Intense
			if(peakAssignmentType == "intense") {
				if(peak[1] > bestPeak[1]) {
					bestPeak = peak;
					continue;
				}
			}
			
			// if peak assignment method is Closest Peak
			if(peakAssignmentType == "close") {
				var dist = Math.abs(ionmz - peak[0]);
				if(!bestDistance || dist < bestDistance) {
					bestPeak = peak;
					bestDistance = dist;
				}
			}
		}
		
		return peakIndex;
	}
	

    function getPeaks(container)
    {
        var options = container.data("options");

        if($(getElementSelector(container, elementIds.peakDetect)).is(":checked"))
        {
            if(options.sparsePeaks == null) {
                doPeakDetection(container);
            }
            return options.sparsePeaks;
        }
        else
        {
            return options.peaks;
        }
    }

    function doPeakDetection(container) {

        // console.log("calculating sparse peaks");

        var peaks = container.data("options").peaks;
        var sparsePeaks = [];

        for(var i = 0; i < peaks.length; i += 1) {

			var peak = peaks[i];

            var intensity = peak[1];
            var mz = peak[0];
            var minMz = mz;
            var maxMz = mz;
            var j = i-1;
            var totalIntensity = intensity;
            var peakCount = 1;
            // sum up the intensities in the +/- 50Da window of this peak
            var maxIntensity = intensity;
            while((minMz >= mz - 50.0) && j >= 0)
            {
                if(peaks[j][1] > maxIntensity)
                {
                    maxIntensity = peaks[j][1];
                }
                totalIntensity += peaks[j][1];
                minMz = peaks[j][0];
                j -= 1;
                peakCount += 1;
            }
            j = i+1;
            while(maxMz <= mz + 50.0 && j < peaks.length)
            {
                if(peaks[j][1] > maxIntensity)
                {
                    maxIntensity = peaks[j][1];
                }
                totalIntensity += peaks[j][1];
                maxMz = peaks[j][0];
                j += 1;
                peakCount += 1;
            }

            var mean = totalIntensity / peakCount;
            if(peakCount <= 10 && intensity == maxIntensity)
            {
                sparsePeaks.push(peak);
            }

            else
            {
                // calculate the standard deviation
                var sdev = 0;
                j = i - 1;
                while((minMz >= mz - 50.0) && j >= 0)
                {
                    sdev += Math.pow((peaks[j][1] - mean), 2);
                    minMz = peaks[j][0];
                    j -= 1;
                }
                j = i+1;
                while(maxMz <= mz + 50.0 && j < peaks.length)
                {
                    sdev += Math.pow((peaks[j][1] - mean), 2);
                    maxMz = peaks[j][0];
                    j += 1;
                }
                sdev = Math.sqrt(sdev / peakCount);

                if(intensity >= mean + 2 * sdev)
                {
                    sparsePeaks.push(peak);
                }
                //console.log(intensity+"  "+mean+"  "+sdev);
            }
		}
        // console.log("Sparse Peak count: "+sparsePeaks.length);
        // console.log("All Peaks count: "+peaks.length);
        container.data("options").sparsePeaks = sparsePeaks;
    }

	// -----------------------------------------------
	// INITIALIZE THE CONTAINER
	// -----------------------------------------------
    function createContainer(div) {

        div.append('<div id="'+elementIds.lorikeet_content+"_"+index+'"></div>');
        var container = $("#"+ div.attr('id')+" > #"+elementIds.lorikeet_content+"_"+index);
        container.addClass("lorikeet");
        return container;
    }

	function initContainer(container) {

        var options = container.data("options");

        var rowspan = 2;

		var parentTable = '<table cellpadding="0" cellspacing="5"> ';
		parentTable += '<tbody> ';
		parentTable += '<tr> ';

		// Header
		parentTable += '<td colspan="3" class="bar"> ';
		parentTable += '</div> ';
		parentTable += '</td> ';
		parentTable += '</tr> ';

		// options table
		parentTable += '<tr> ';
		parentTable += '<td rowspan="'+rowspan+'" valign="top" id="'+getElementId(container, elementIds.optionsTable)+'"> ';
		parentTable += '</td> ';

        if(options.showSequenceInfo) {
            // placeholder for sequence, m/z, scan number etc
            parentTable += '<td style="background-color: white; padding:5px; border:1px dotted #cccccc;" valign="bottom" align="center"> ';
            parentTable += '<div id="'+getElementId(container, elementIds.seqinfo)+'" style="width:100%;"></div> ';
            // placeholder for file name, scan number and charge
            parentTable += '<div id="'+getElementId(container, elementIds.fileinfo)+'" style="width:100%;"></div> ';
            parentTable += '</td> ';
        }


        if(options.showIonTable) {
            // placeholder for the ion table
            parentTable += '<td rowspan="'+rowspan+'" valign="top" id="'+getElementId(container, elementIds.ionTableLoc1)+'" > ';
            parentTable += '<div id="'+getElementId(container, elementIds.ionTableDiv)+'">';
            parentTable += '<span id="'+getElementId(container, elementIds.moveIonTable)+'" class="font_small link">[Click]</span> <span class="font_small">to move table</span>';
            // placeholder for modifications
            parentTable += '<div id="'+getElementId(container, elementIds.modInfo)+'" style="margin-top:5px;"></div> ';
            parentTable += '</div> ';
            parentTable += '</td> ';
            parentTable += '</tr> ';
        }


		// placeholders for the ms/ms plot
		parentTable += '<tr> ';
		parentTable += '<td style="background-color: white; padding:5px; border:1px dotted #cccccc;" valign="top" align="center"> ';
		parentTable += '<div id="'+getElementId(container, elementIds.msmsplot)+'" align="bottom" style="width:'+options.width+'px;height:'+options.height+'px;"></div> ';

		// placeholder for viewing options (zoom, plot size etc.)
		parentTable += '<div id="'+getElementId(container, elementIds.viewOptionsDiv)+'" align="top" style="margin-top:15px;"></div> ';

		// placeholder for ms1 plot (if data is available)
		if(options.ms1peaks && options.ms1peaks.length > 0) {
			parentTable += '<div id="'+getElementId(container, elementIds.msPlot)+'" style="width:'+options.width+'px;height:100px;"></div> ';
		}
		parentTable += '</td> ';
		parentTable += '</tr> ';


		// Footer & placeholder for moving ion table
		parentTable += '<tr> ';
		parentTable += '<td colspan="3" class="bar noprint" valign="top" align="center" id="'+getElementId(container, elementIds.ionTableLoc2)+'" > ';
		parentTable += '<div align="center" style="width:100%;font-size:10pt;"> ';
		parentTable += '</div> ';
		parentTable += '</td> ';
		parentTable += '</tr> ';


        if(options.showAllTable) {
            parentTable += '<tr> ';
            parentTable += '<td colspan="3" class="bar noprint" valign="top" align="center" id="'+getElementId(container, elementIds.allTableLoc)+'" > ';
            parentTable += '<div align="center" style="width:100%;font-size:10pt;"> ';
            parentTable += '</div> ';
            parentTable += '</td> ';
            parentTable += '</tr> ';
        }

		parentTable += '</tbody> ';
		parentTable += '</table> ';

		container.append(parentTable);
		
		return container;
	}
	
	
	//---------------------------------------------------------
	// ION TABLE
	//---------------------------------------------------------
	function makeIonTable(container) {

        var options = container.data("options");

	 	// selected ions
		var selectedIonTypes = getSelectedIonTypes(container);
		var ntermIons = getSelectedNtermIons(selectedIonTypes);
		var ctermIons = getSelectedCtermIons(selectedIonTypes);
		
		var myTable = '' ;
		myTable += '<table id="'+getElementId(container, elementIds.ionTable)+'" cellpadding="2" class="font_small '+elementIds.ionTable+'">' ;
		myTable +=  "<thead>" ;
		myTable +=   "<tr>";

		// nterm ions
		for(var i = 0; i < ntermIons.length; i += 1) {
			myTable +=    "<th>" +ntermIons[i].label+  "</th>";   
		}
		myTable +=    "<th>" +"#"+  "</th>"; 
		myTable +=    "<th>" +"Seq"+  "</th>"; 
		myTable +=    "<th>" +"#"+  "</th>"; 
		// cterm ions
		for(var i = 0; i < ctermIons.length; i += 1) {
			myTable +=    "<th>" +ctermIons[i].label+  "</th>"; 
		}
		myTable +=   "</tr>" ;
		myTable +=  "</thead>" ;
		
		myTable +=  "<tbody>" ;

        var ionSeries = container.data("ionSeries");

		for(var i = 0; i < options.sequence.length; i += 1) {
            var aaChar = options.sequence.charAt(i);
			myTable +=   "<tr>";

			// nterm ions
			for(var n = 0; n < ntermIons.length; n += 1) {
				if(i < options.sequence.length - 1) {
					var seriesData = getCalculatedSeries(ionSeries, ntermIons[n]);
					var cls = "";
					var style = "";
					if(seriesData[i].match) {
						cls="matchIon";
						style="style='background-color:"+Ion.getSeriesColor(ntermIons[n])+";'";
					}
					myTable +=    "<td class='"+cls+"' "+style+" >" +round(seriesData[i].mz)+  "</td>";  
				}
				else {
					myTable +=    "<td>" +"&nbsp;"+  "</td>"; 
				} 
			}
			
			myTable += "<td class='numCell'>"+(i+1)+"</td>";
			if(options.peptide.varMods()[i+1])
				myTable += "<td class='seq modified'>"+aaChar+"</td>";
			else
				myTable += "<td class='seq'>"+aaChar+"</td>";
			myTable += "<td class='numCell'>"+(options.sequence.length - i)+"</td>";
			
			// cterm ions
			for(var c = 0; c < ctermIons.length; c += 1) {
				if(i > 0) {
					var seriesData = getCalculatedSeries(ionSeries, ctermIons[c]);
					var idx = options.sequence.length - i - 1;
					var cls = "";
					var style = "";
					if(seriesData[idx].match) {
						cls="matchIon";
						style="style='background-color:"+Ion.getSeriesColor(ctermIons[c])+";'";
					}
					myTable +=    "<td class='"+cls+"' "+style+" >" +round(seriesData[idx].mz)+  "</td>";  
				}
				else {
					myTable +=    "<td>" +"&nbsp;"+  "</td>"; 
				} 
			}
			
		}
		myTable +=   "</tr>" ;
		
		myTable += "</tbody>";
		myTable += "</table>";

        $(getElementSelector(container, elementIds.internalIonTable)).remove();
        if(internalIonsEnabled(container) && options.showInternalIonsTable) {
            myTable += makeInternalIonsTable(container);
        }
		
		// alert(myTable);
		$(getElementSelector(container, elementIds.ionTable)).remove();
		$(getElementSelector(container, elementIds.ionTableDiv)).prepend(myTable); // add as the first child

        if(allIonsEnabled(container)) {
            $(getElementSelector(container, elementIds.allTableLoc)).html(makeAllIonsTable(container));
        }


	}
	
	function getCalculatedSeries(ionSeries, ion) {
        if(ion.type == "a")
			return ionSeries.a[ion.charge];
		if(ion.type == "b")
			return ionSeries.b[ion.charge];
		if(ion.type == "c")
			return ionSeries.c[ion.charge];
		if(ion.type == "x")
			return ionSeries.x[ion.charge];
		if(ion.type == "y")
			return ionSeries.y[ion.charge];
		if(ion.type == "z")
			return ionSeries.z[ion.charge];
        if(ion.type == "mh")
            return ionSeries.mh[ion.charge];
	}
	
	function makeIonTableMovable(container) {

		$(getElementSelector(container, elementIds.moveIonTable)).hover(
			function(){
		         $(this).css({cursor:'pointer'}); //mouseover
		    }
		);

		$(getElementSelector(container, elementIds.moveIonTable)).click(function() {
			var ionTableDiv = $(getElementSelector(container, elementIds.ionTableDiv));
			if(ionTableDiv.is(".moved")) {
				ionTableDiv.removeClass("moved");
				ionTableDiv.detach();
				$(getElementSelector(container, elementIds.ionTableLoc1)).append(ionTableDiv);
			}
			else {
				ionTableDiv.addClass("moved");
				ionTableDiv.detach();
				$(getElementSelector(container, elementIds.ionTableLoc2)).append(ionTableDiv);
			}
		});
	}

	//---------------------------------------------------------
	// SEQUENCE INFO
	//---------------------------------------------------------
	function showSequenceInfo (container) {

        var options = container.data("options");

		var specinfo = '';
		if(options.sequence) {
			
			specinfo += '<div>';
			specinfo += '<span style="font-weight:bold; color:#8B0000;">'+getModifiedSequence(options)+'</span>';
			
			var massType = container.find("input[name='"+getRadioName(container, "massTypeOpt")+"']:checked").val();
			
			var neutralMass = 0;
			
			if(options.precursorMassType == 'mono')
               neutralMass = options.peptide.getNeutralMassMono();
            else
		        neutralMass = options.peptide.getNeutralMassAvg();
				
			
			var mz;
			if(options.charge) {
				mz = Ion.getMz(neutralMass, options.charge);
			}
			
			var mass = neutralMass + Ion.MASS_PROTON;
			specinfo += ', MH+ '+mass.toFixed(4);
			if(mz) 
				specinfo += ', m/z '+mz.toFixed(4);
			specinfo += '</div>';
			
		}
		
		// first clear the div if it has anything
		$(getElementSelector(container, elementIds.seqinfo)).empty();
		$(getElementSelector(container, elementIds.seqinfo)).append(specinfo);
	}
	
	function getModifiedSequence(options) {
		
		var modSeq = '';
		for(var i = 0; i < options.sequence.length; i += 1) {
			
			if(options.peptide.varMods()[i+1])
				modSeq += '<span style="background-color:yellow;padding:1px;border:1px dotted #CFCFCF;">'+options.sequence.charAt(i)+"</span>";
			else
				modSeq += options.sequence.charAt(i);
		}
		
		return modSeq;
	}
	
	//---------------------------------------------------------
	// FILE INFO -- filename, scan number, precursor m/z and charge
	//---------------------------------------------------------
	function showFileInfo (container) {

        var options = container.data("options");

		var fileinfo = '';
			
		if(options.fileName || options.scanNum) {
			fileinfo += '<div style="margin-top:5px;" class="font_small">';
			if(options.fileName) {
				fileinfo += 'File: '+options.fileName;
			}
			if(options.scanNum) {
				fileinfo += ', Scan: '+options.scanNum;
			}
			if(options.charge) {
				fileinfo += ', Charge: '+options.charge;
			}
			fileinfo += '</div>';
		}
		
		$(getElementSelector(container, elementIds.fileinfo)).append(fileinfo);
	}
	
	//---------------------------------------------------------
	// MODIFICATION INFO
	//---------------------------------------------------------
	function showModInfo (container) {

        var options = container.data("options");

		var modInfo = '';
			
		modInfo += '<div>';
		if(options.ntermMod || options.ntermMod > 0) {
			modInfo += 'Add to N-term: <b>'+options.ntermMod+'</b>';
		}
		if(options.ctermMod || options.ctermMod > 0) {
			modInfo += 'Add to C-term: <b>'+options.ctermMod+'</b>';
		}
		modInfo += '</div>';
		
		if(options.staticMods && options.staticMods.length > 0) {
			modInfo += '<div style="margin-top:5px;">';
			modInfo += 'Static Modifications: ';
			for(var i = 0; i < options.staticMods.length; i += 1) {
				var mod = options.staticMods[i];
				//if(i > 0) modInfo += ', ';
				modInfo += "<div><b>"+mod.aa.code+": "+mod.modMass+"</b></div>";
			}
			modInfo += '</div>';
		}
		
		if(options.variableMods && options.variableMods.length > 0) {
			
			var uniqVarMods = {};
			for(var i = 0; i < options.variableMods.length; i += 1) {
				var mod = options.variableMods[i];
                var varmods = uniqVarMods[mod.aa.code + ' ' + mod.modMass];
				if(!varmods)
                {
					varmods = [];
                    uniqVarMods[mod.aa.code + ' ' + mod.modMass] = varmods;
                }
				varmods.push(mod);
			}  

            var keys = [];
            for(var key in uniqVarMods)
            {
                if(uniqVarMods.hasOwnProperty(key))
                {
                    keys.push(key);
                }
            }
            keys.sort();

			modInfo += '<div style="margin-top:5px;">';
			modInfo += 'Variable Modifications: ';
            modInfo += "<table class='varModsTable'>";
			for(var k = 0; k < keys.length; k++) {
				var varmods = uniqVarMods[keys[k]];
                modInfo += "<tr><td><span style='font-weight: bold;'>";
                modInfo += varmods[0].aa.code+": "+varmods[0].modMass;
                modInfo += "</span></td>";
                modInfo += "<td>[";
                for(var i = 0; i < varmods.length; i++)
                {
                    if(i != 0)
                        modInfo += ", ";
                    modInfo += varmods[i].position;
                }
                modInfo += "]</td>";
                modInfo += "</tr>";
			}
            modInfo += "</table>";
			modInfo += '</div>';
		}
		
		$(getElementSelector(container, elementIds.modInfo)).append(modInfo);
	}
	
	//---------------------------------------------------------
	// VIEWING OPTIONS TABLE
	//---------------------------------------------------------
	function makeViewingOptions(container) {

        var options = container.data("options");

		var myContent = '';
		
		// reset zoom option
		myContent += '<nobr> ';
		myContent += '<span style="width:100%; font-size:8pt; margin-top:5px; color:sienna;">Click and drag in the plot to zoom</span> ';
		myContent += 'X:<input id="'+getElementId(container, elementIds.zoom_x)+'" type="checkbox" value="X" checked="checked"/> ';
		myContent += '&nbsp;Y:<input id="'+getElementId(container, elementIds.zoom_y)+'" type="checkbox" value="Y" /> ';
		myContent += '&nbsp;<input id="'+getElementId(container, elementIds.resetZoom)+'" type="button" value="Zoom Out" /> ';
		myContent += '&nbsp;<input id="'+getElementId(container, elementIds.printLink)+'" type="button" value="Print" /> ';
		myContent += '</nobr> ';
		
		myContent += '&nbsp;&nbsp;';
		
		// tooltip option
		myContent += '<nobr> ';
		myContent += '<input id="'+getElementId(container, elementIds.enableTooltip)+'" type="checkbox">Enable tooltip ';
		myContent += '</nobr> ';
		
		myContent += '<br>';
		
		$(getElementSelector(container, elementIds.viewOptionsDiv)).append(myContent);
		if(!options.showViewingOptions) {
            $(getElementSelector(container, elementIds.viewOptionsDiv)).hide();
        }
	}
	
	
	//---------------------------------------------------------
	// OPTIONS TABLE
	//---------------------------------------------------------
	function makeOptionsTable(container, charge) {

        var options = container.data("options");

		var myTable = '';
		myTable += '<table cellpadding="2" cellspacing="2"> ';
		myTable += '<tbody> ';
		
		// Ions
		myTable += '<tr><td class="optionCell"> ';
		
		myTable += '<b>Ions:</b> ';
		myTable += '<div id="'+getElementId(container, elementIds.ion_choice)+'" style="margin-bottom: 10px"> ';
		myTable += '<!-- a ions --> ';
		myTable += '<nobr> ';
		myTable += '<span style="font-weight: bold;">a</span> ';
		myTable += '<input type="checkbox" value="1" id="a_1"/>1<sup>+</sup> ';
		myTable += '<input type="checkbox" value="2" id="a_2"/>2<sup>+</sup> ';
		myTable += '<input type="checkbox" value="3" id="a_3"/>3<sup>+</sup> ';
		myTable += '</nobr> ';
		myTable += '<br/> ';
		myTable += '<!-- b ions --> ';
		myTable += '<nobr> ';
		myTable += '<span style="font-weight: bold;">b</span> ';
		myTable += '<input type="checkbox" value="1" id="b_1" checked="checked"/>1<sup>+</sup> ';
		if(charge >= 2)
			myTable += '<input type="checkbox" value="2" id="b_2" checked="checked"/>2<sup>+</sup> ';
		else
			myTable += '<input type="checkbox" value="2" id="b_2"/>2<sup>+</sup> ';
		if(charge >= 3)
			myTable += '<input type="checkbox" value="3" id="b_3" checked="checked"/>3<sup>+</sup> ';
		else
			myTable += '<input type="checkbox" value="3" id="b_3"/>3<sup>+</sup> ';
		myTable += '</nobr> ';
		myTable += '<br/> ';
		myTable += '<!-- c ions --> ';
		myTable += '<nobr> ';
		myTable += '<span style="font-weight: bold;">c</span> ';
		myTable += '<input type="checkbox" value="1" id="c_1"/>1<sup>+</sup> ';
		myTable += '<input type="checkbox" value="2" id="c_2"/>2<sup>+</sup> ';
		myTable += '<input type="checkbox" value="3" id="c_3"/>3<sup>+</sup> ';
		myTable += '</nobr> ';
		myTable += '<br/> ';
		myTable += '<!-- x ions --> ';
		myTable += '<nobr> ';
		myTable += '<span style="font-weight: bold;">x</span> ';
		myTable += '<input type="checkbox" value="1" id="x_1"/>1<sup>+</sup> ';
		myTable += '<input type="checkbox" value="2" id="x_2"/>2<sup>+</sup> ';
		myTable += '<input type="checkbox" value="3" id="x_3"/>3<sup>+</sup> ';
		myTable += '</nobr> ';
		myTable += '<br/> ';
		myTable += '<!-- y ions --> ';
		myTable += '<nobr> ';
		myTable += '<span style="font-weight: bold;">y</span> ';
		myTable += '<input type="checkbox" value="1" id="y_1" checked="checked"/>1<sup>+</sup> ';
		if(charge >= 2)
			myTable += '<input type="checkbox" value="2" id="y_2" checked="checked"/>2<sup>+</sup> ';
		else 
			myTable += '<input type="checkbox" value="2" id="y_2"/>2<sup>+</sup> ';
		if(charge >= 3)
			myTable += '<input type="checkbox" value="3" id="y_3" checked="checked"/>3<sup>+</sup> ';
		else
			myTable += '<input type="checkbox" value="3" id="y_3"/>3<sup>+</sup> ';
		myTable += '</nobr> ';
		myTable += '<br/> ';
		myTable += '<!-- z ions --> ';
		myTable += '<nobr> ';
		myTable += '<span style="font-weight: bold;">z</span> ';
		myTable += '<input type="checkbox" value="1" id="z_1"/>1<sup>+</sup> ';
		myTable += '<input type="checkbox" value="2" id="z_2"/>2<sup>+</sup> ';
		myTable += '<input type="checkbox" value="3" id="z_3"/>3<sup>+</sup> ';
		myTable += '</nobr> ';
		myTable += '<br/> ';

        if(options.showMHIonOption) {
            myTable += '<div><span style="font-weight: bold;">MH</span> ';
            myTable += '<input type="checkbox" value="1" id="mh_1"/>1<sup>+</sup> ';
            myTable += '<input type="checkbox" value="2" id="mh_2"/>2<sup>+</sup> ';
            myTable += '</nobr> ';
            myTable += '<br/> ';
        }

        if(options.showInternalIonOption) {
            myTable += '<div><span style="font-weight: bold;">Internal</span><input type="checkbox" value="internal" id="internal"/> ';
            myTable += '</nobr><br />';
        }
		myTable += '<span id="'+getElementId(container, elementIds.deselectIonsLink)+'" style="font-size:8pt;text-decoration: underline; color:sienna;cursor:pointer;">[Deselect All]</span> ';
		myTable += '</div><br /> ';
		
		myTable += '<span style="font-weight: bold;">Neutral Loss:</span> ';
		myTable += '<div id="'+getElementId(container, elementIds.nl_choice)+'"> ';
		myTable += '<nobr> <input type="checkbox" value="h2o" id="h2o"/> ';
		myTable += ' H<sub>2</sub>O (<span style="font-weight: bold;">o</span>)';
		myTable += '</nobr> ';
		myTable += '<br> ';
		myTable += '<nobr> <input type="checkbox" value="nh3" id="nh3"/> ';
		myTable += ' NH<sub>3</sub> (<span style="font-weight: bold;">*</span>)';
		myTable += '</nobr> ';
		myTable += '</div> ';
		
		myTable += '</td> </tr> ';
		
		// mass type, mass tolerance etc.
		myTable += '<tr><td class="optionCell"> ';
		myTable += '<div> Mass Type:<br/> ';
		myTable += '<nobr> ';
		myTable += '<input type="radio" name="'+getRadioName(container, "massTypeOpt")+'" value="mono"';
        if(options.fragmentMassType == 'mono')
            myTable += ' checked = "checked" ';
        myTable += '/><span style="font-weight: bold;">Mono</span> ';
		myTable += '<input type="radio" name="'+getRadioName(container, "massTypeOpt")+'" value="avg"';
        if(options.fragmentMassType == 'avg')
            myTable += ' checked = "checked" ';
        myTable += '/><span style="font-weight: bold;">Avg</span> ';
		myTable += '</nobr> ';
		myTable += '</div> ';
		myTable += '<div style="margin-top:10px;"> ';
		myTable += '<nobr>Mass Tol: <input id="'+getElementId(container, elementIds.massError)+'" type="text" value="'+options.massError+'" size="4"/></nobr> ';
		myTable += '</div> ';
		myTable += '<div style="margin-top:10px;" align="center"> ';
		myTable += '<input id="'+getElementId(container, elementIds.update)+'" type="button" value="Update"/> ';
		myTable += '</div> ';
		myTable += '</td> </tr> ';
		
		// peak assignment method
		myTable += '<tr><td class="optionCell"> ';
		myTable+= '<div> Peak Assignment:<br/> ';
		myTable+= '<input type="radio" name="'+getRadioName(container, "peakAssignOpt")+'" value="intense" checked="checked"/><span style="font-weight: bold;">Most Intense</span><br/> ';
		myTable+= '<input type="radio" name="'+getRadioName(container, "peakAssignOpt")+'" value="close"/><span style="font-weight: bold;">Nearest Match</span><br/> ';
        myTable+= '<input type="checkbox" value="true" ';
        if(options.peakDetect == true)
        {
            myTable+=checked="checked"
        }
        myTable+= ' id="'+getElementId(container, elementIds.peakDetect)+'"/><span style="font-weight:bold;">Peak Detect</span>';
		myTable+= '</div> ';
		myTable += '</td> </tr> ';
		
		// peak labels
		myTable += '<tr><td class="optionCell"> ';
		myTable+= '<div> Peak Labels:<br/> ';
		myTable+= '<input type="radio" name="'+getRadioName(container, "peakLabelOpt")+'" value="ion" checked="checked"/><span style="font-weight: bold;">Ion</span>';
		myTable+= '<input type="radio" name="'+getRadioName(container, "peakLabelOpt")+'" value="mz"/><span style="font-weight: bold;">m/z</span><br/>';
		myTable+= '<input type="radio" name="'+getRadioName(container, "peakLabelOpt")+'" value="none"/><span style="font-weight: bold;">None</span> ';
		myTable+= '</div> ';
		myTable += '</td> </tr> ';
		
		// sliders to change plot size
		myTable += '<tr><td class="optionCell"> ';
		myTable += '<div>Width: <span id="'+getElementId(container, elementIds.slider_width_val)+'">'+options.width+'</span></div> ';
		myTable += '<div id="'+getElementId(container, elementIds.slider_width)+'" style="margin-bottom:15px;"></div> ';
		myTable += '<div>Height: <span id="' + getElementId(container, elementIds.slider_height_val) + '">' + options.height + '</span></div> ';
		myTable += '<div id="'+getElementId(container, elementIds.slider_height)+'"></div> ';
		myTable += '</td> </tr> ';

		myTable += '</tbody>';
		myTable += '</table>';

		$(getElementSelector(container, elementIds.optionsTable)).append(myTable);
        if(!options.showOptionsTable) {
            $(getElementSelector(container, elementIds.optionsTable)).hide();
        }
	}

	
})(jQuery);

// Cookie functions from:
// http://www.quirksmode.org/js/cookies.html
function createCookie(name,value,days) {
	if (days) {
		var date = new Date();
		date.setTime(date.getTime()+(days*24*60*60*1000));
		var expires = "; expires="+date.toGMTString();
	}
	else var expires = "";
	var value = name+"="+value+expires+"; path=/";
	document.cookie = value;
	
}

function readCookie(name) {
	var nameEQ = name + "=";
	var ca = document.cookie.split(';');
	for(var i=0;i < ca.length;i++) {
		var c = ca[i];
		while (c.charAt(0)==' ') c = c.substring(1,c.length);
		if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
	}
	return null;
}
