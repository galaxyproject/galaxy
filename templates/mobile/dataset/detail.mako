<div id="dataset_${dataset.id}" title="Dataset" class="panel">
    <div class="toolbar">
        <h1>${dataset.display_name()}</h1>
        <a class="back button" href="#">Back</a>
    </div>

    <div class="pad">
      <fieldset>
      <div class="row">
	<label>State</label> <span>${dataset.state}</span>
      </div>
      <div class="row">
	<label>Content</label> <span>${dataset.blurb}</span>
      </div>
      <div class="row">
        <label>Format</label> <span>${dataset.ext}</span>
      </div>
      <div class="row">
	<label>Info</label> <span>${dataset.display_info()}</span>
      </div>
      %if dataset.state == "ok":
      <div class="row">
	        <a href="${h.url_for( action='dataset_peek', id=dataset.id )}">Peek</a>
      </div>
      %endif
      </fieldset>
    </div>
 
</body>
