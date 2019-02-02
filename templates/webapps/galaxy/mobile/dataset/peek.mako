<div id="dataset_peek_${dataset.id}" title="Dataset Peek" class="panel">
    <div class="toolbar">
        <h1>${dataset.display_name()}</h1>
        <a class="back button" href="#">Back</a>
    </div>

    <div class="pad" style="overflow: auto;">
        <pre>
            ${dataset.display_peek()}
        </pre>
    </div>
</div>
