<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
	"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
	<head>
		<title>
			Galaxy
		</title>
		<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
		<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />

		<script type='text/javascript' src="${h.url_for('/static/scripts/jquery.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/scripts/jquery.ui.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/scripts/jquery.event.drag.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/scripts/jquery.hoverIntent.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/scripts/jamal.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/tracks/app_model.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/tracks/app_controller.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/tracks/app_view.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/tracks/models/tracks.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/tracks/views/viewport.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/tracks/views/drawing_api.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/tracks/controllers/tracks.js')}"> </script>
		<script type='text/javascript' src="${h.url_for('/static/tracks/views/components.js')}"> </script>
  		<link type="text/css" rel="stylesheet" href="http://ui.jquery.com/testing/themes/base/ui.all.css" />
		<link href="${h.url_for('/static/tracks/app.css')}" rel="stylesheet" type="text/css" />
	</head>
	<body class="jamal {controller:'Viewport',action:'index',debug:true}">
		<div id="viewport" class="float-left">
			<div id="viewport-top" class="width-hundred-percent block overflow">
				<div class="float-left width-twenty-percent">
					<div id="db-tools" class="width-hundred-percent block">
						<h2 class="margin-zero">db: </h2>
						<select name="dbkey" id="dbkey"> </select>
						<select name="chrom" id="chrom"> </select>
					</div>
					<div id="history-tools" class="width-hundred-percent block">
						<a href="#" id="show-history" class="float-left margin-zero padding-zero">
							<img src="${h.url_for('/static/images/tracks/show_history.gif')}">
						</a>
					</div>
				</div>
				<div class="float-left width-eighty-percent">
					<div id="window-macro" class="width-hundred-percent block">
						<div id="macro-slider"> </div>
					</div>
					<div id="window-micro" class="width-hundred-percent block">
						<canvas id="x-axis" class="axis width-hundred-percent float-left"></canvas> 
					</div>
				</div>
			</div>
			<div id="viewport-inner" class="width-hundred-percent block">
				<ul id="tracks-sortable" class="width-hundred-percent padding-zero margin-zero">
					<li class="track-list-item width-hundred-percent" id="item_1">
						<div id="t11" class="track width-hundred-percent no-overflow margin-zero">
							<div class="track-label margin-zero float-left width-twenty-percent">
								<h5 class="track-title">mRNA</h5>
							</div>
							<div class="track-track margin-zero float-left width-eighty-percent">
								<div id="track-graphics">
									<canvas class="track-canvas width-hundred-percent"> </canvas>
								</div>
							</div>
						</div>
					</li>
				</ul>
			</div>
			<div id="dock" class="padding-zero width-sixty-percent">
				<ul>
					<li><select name="chrom" id="chrom-select">	</select></li>
					<li><input type="text" id="position-window" /></li>
					<li><a id="go-btn" href="#"><img src="${h.url_for('/static/images/tracks/go_btn.gif')}"/></a></li>
					<li><a id="pan-left" href="#"><img src="${h.url_for('/static/images/tracks/pan_left.gif')}"/></a></li>
					<li><a id="pan-right" href="#"><img src="${h.url_for('/static/images/tracks/pan_right.gif')}"/></a></li>
					<li><a id="zoom-out-full" href="#"><img src="${h.url_for('/static/images/tracks/zoom_out_full.gif')}"/></a></li>
					<li><a id="zoom-out" href="#"><img src="${h.url_for('/static/images/tracks/zoom_out.gif')}"/></a></li>
					<li><a id="zoom-in" href="#"><img src="${h.url_for('/static/images/tracks/zoom_in.gif')}"/></a></li>		
					<li><a id="zoom-in-full" href="#"><img src="${h.url_for('/static/images/tracks/zoom_in_full.gif')}"/></a></li>
				</ul>
			</div>
		</div>
		<div id="drag-history" class="float-left margin-zero">
			<div id="history-control-bar" class="width-hundred-percent">
				<div class="width-sixty-percent float-left">
					<h3 class="margin-zero">History</h3>
				</div>
				<div class="width-forty-percent float-left">
					<a id="hide-history" href="#">
						<img src="${h.url_for('/static/images/tracks/close_btn.gif')}"/>
					</a>
				</div>
			</div>
			<ul id="tracks-history-sortable">
				<li class="track-history-item" id="item_1">
					<div class="history-item" id="history-item-1">
						<div class="history-edit-panel"> </div>
						<span class="history-item-title">
							<b>3: UCSC Main on Human: knownGene (genome)</b>
						<span>
					</div>
				</li>
			</ul>
		</div>		
	</body>
</html>
