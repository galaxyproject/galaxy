%for jobentry in jobs:
    <div class="${jobentry['style']} dialog-box" id="job${jobentry['jobid']}" data-state="${jobentry['state']}" data-jobid="${jobentry['jobid']}" data-type="${jobentry['type']}">
        <span class="inline">${jobentry['type']}</span>
    </div>
%endfor
