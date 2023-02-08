$('#config_host').load( "config_host.html" );
$('#config_hub').load( "config_hub.html" );
$('#config_switch').load( "config_switch.html" );

const config_content_id = "#config_content";
const config_main_form_id = "#config_main_form";
const config_hub_main_form_id = "#config_hub_main_form";
const config_switch_main_form_id = "#config_switch_main_form";

const ClearConfigForm = function(text){

    let txt = ''

    if (!text)
    {
        txt = 'Тут будут настройки устройств. Выделите любое на схеме.';
    }

    // Clear all child
    $(config_content_id).empty();
    $(config_content_id).append('<h4>' + txt + '</h4>');
}

const ConfigHostForm = function(host_id){
    var form = document.getElementById('config_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#host_id').val( host_id );
    $('#net_guid').val( network_guid );

    $('#config_main_form_submit_button').click(function(event) {
        event.preventDefault();
        let data = $('#config_main_form').serialize();

        // Disable all input fields
        $("#config_main_form :input").prop("disabled", true);

        // Set loading spinner
        $(this).text('');
        $(this).append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

        UpdateHostConfiguration(data, host_id);
    });
}

const ConfigHubForm = function(hub_id){
    var form = document.getElementById('config_hub_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#hub_id').val( hub_id );
    $('#net_guid').val( network_guid );

    $('#config_hub_main_form_submit_button').click(function(event) {
        event.preventDefault();
        let data = $('#config_hub_main_form').serialize();

        // Disable all input fields
        $("#config_hub_main_form :input").prop("disabled", true);

        // Set loading spinner
        $(this).text('');
        $(this).append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

        UpdateHubConfiguration(data, hub_id);
    });
}

const ConfigSwitchForm = function(switch_id){
    var form = document.getElementById('config_switch_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#switch_id').val( switch_id );
    $('#net_guid').val( network_guid );

    $('#config_switch_main_form_submit_button').click(function(event) {
        event.preventDefault();
        let data = $('#config_switch_main_form').serialize();

        // Disable all input fields
        $("#config_switch_main_form :input").prop("disabled", true);

        // Set loading spinner
        $(this).text('');
        $(this).append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

        UpdateSwitchConfiguration(data, switch_id);
    });
}

const ConfigHubName = function(hostname){

    var text = document.getElementById('config_hub_name_script').innerHTML;

    $(config_hub_main_form_id).prepend((text));
    $('#config_hub_name').val(hostname);
}

const ConfigSwitchName = function(hostname){

    var text = document.getElementById('config_switch_name_script').innerHTML;

    $(config_switch_main_form_id).prepend((text));
    $('#config_switch_name').val(hostname);
}

const SharedConfigHostForm = function(host_id){
    var form = document.getElementById('config_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#host_id').val( host_id );
    $('#net_guid').val( network_guid );
    $('#config_main_form_submit_button').prop('disabled', true);
}

const SharedConfigHubForm = function(hub_id){
    var form = document.getElementById('config_hub_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);
    $('#config_hub_main_form_submit_button').prop('disabled', true);
}

const SharedConfigSwitchForm = function(switch_id){
    var form = document.getElementById('config_switch_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);
    $('#config_switch_main_form_submit_button').prop('disabled', true);
}

const ConfigHostName = function(hostname){

    var text = document.getElementById('config_host_name_script').innerHTML;

    $(config_main_form_id).prepend((text));
    $('#config_host_name').val(hostname);
}

const ConfigHostInterface = function(name, ip, netmask, connected_to){

    let elem = document.getElementById('config_host_interface_script');
    let eth = jQuery.extend({}, elem);

    if (!name){
        return;
    }

    eth.innerHTML = eth.innerHTML.replace(/config_host_iface_name_label_example/g, 'config_host_iface_name_label_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_host_iface_name_example/g, 'config_host_iface_name_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_host_ip_example/g, 'config_host_ip_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_host_mask_example/g, 'config_host_mask_' + name);

    var text = eth.innerHTML;

    $(text).insertBefore('#config_main_form_submit_button');
    $('<input type="hidden" name="config_host_iface_ids[]" value="' + name + '"/>').insertBefore('#config_host_iface_name_' + name);
    $('#config_host_iface_name_' + name).attr("placeholder", connected_to);
    $('#config_host_ip_' + name).val(ip);
    $('#config_host_mask_' + name).val(netmask);

}

const ConfigHostJobOnChange = function(evnt){

    switch(evnt.target.value)
    {
        case '1':
            let elem = document.getElementById('config_host_ping_c_1_script').innerHTML;
            let host_job_list = document.getElementById('config_host_job_list');

            if (!elem || !host_job_list){
                return;
            }

            $(elem).insertBefore(host_job_list);
            break;

        case '0':
            $('div[name="config_host_select_input"]').remove();
            break;

        default:
            console.log("Unknown target.value");
    }

}

const ConfigHostJob = function(host_jobs){

    let elem = document.getElementById('config_host_job_script').innerHTML;
    let host_id = document.getElementById('host_id');

    if (!elem || !host_id){
        return;
    }

    $(elem).insertBefore(host_id);

    // Set onchange
    document.getElementById('config_host_job_select_field').addEventListener('change', ConfigHostJobOnChange);

    elem = document.getElementById('config_host_job_list_script').innerHTML;
    if (!elem){
        return;
    }

    $(elem).insertBefore(host_id);

    // Print jobs if we have
    if (!host_jobs)
    {
        return;
    }

    $.each(host_jobs, function (i) {
        let jid = host_jobs[i].id;

        if (i == 0){
            $('#config_host_job_list').append('<label class="text-sm">Команды</label>');
        }

        elem = document.getElementById('config_host_job_list_elem_script');

        if (!elem){
            return;
        }

        let job_elem = jQuery.extend({}, elem);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_host_job_delete/g, 'config_host_job_delete_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/justify-content-between align-items-center\">/, 'justify-content-between align-items-center\"><small>' + host_jobs[i].print_cmd + '</small>');

        let text = job_elem.innerHTML;
        //$(text).insertBefore(host_id);
        $('#config_host_job_list').append(text);

        $('#config_host_job_delete_' + jid).click(function(event) {
            event.preventDefault();
            DeleteJobFromHost(host_id.value, jid, network_guid);
        });
    });
}