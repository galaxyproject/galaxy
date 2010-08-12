##
## Generate the content block for a myExperiment request.
##
<%!
    from xml.sax.saxutils import escape
    import textwrap, base64 
%>
<galaxy_json>
    ${workflow_dict_packed}
</galaxy_json>
<steps>
    %for step_num, step in workflow_steps.items():
    <step>
        <id>${step_num}</id>
        <name>${step['name']}</name>
        <tool>${step['tool_id']}</tool>
        <description>${escape( step['annotation'] )}</description>
        <inputs>
            %for input in step['inputs']:
            <input>
                <name>${escape( input['name'] )}</name>
                <description>${escape( input['description'] )}</description>
            </input>
            %endfor
        </inputs>
        <outputs>
            %for output in step['outputs']:
            <output>
                <name>${escape( output['name'] )}</name>
                <type>${output['type']}</type>
            </output>
            %endfor
        </outputs>
    </step>
    %endfor
</steps>
<connections>
    %for step_num, step in workflow_steps.items():
        %for input_name, input_connection in step['input_connections'].items():
        <connection>
            <source_id>${input_connection['id']}</source_id>
            <source_output>${input_connection['output_name']}</source_output>
            <sink_id>${step_num}</sink_id>
            <sink_input>${input_name}</sink_input>
        </connection>
        %endfor
    %endfor
</connections>