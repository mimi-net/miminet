const SharedConfigHostForm = function(host_id){
    var form = document.getElementById('config_host_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();
    document.getElementById(config_content_save_id).style.display='none';

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#host_id').val( host_id );
    $('#net_guid').val( network_guid );
    $('#config_host_main_form_submit_button').prop('disabled', true);
}

const SharedConfigRouterForm = function (router_id) {
    var form = document.getElementById('config_router_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();
    document.getElementById(config_content_save_id).style.display='none';

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#router_id').val(router_id);
    $('#net_guid').val(network_guid);

    $('#config_router_main_form_submit_button').prop('disabled', true);
}

const SharedConfigServerForm = function (router_id) {
    var form = document.getElementById('config_server_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();
    document.getElementById(config_content_save_id).style.display='none';

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#router_id').val(router_id);
    $('#net_guid').val(network_guid);

    $('#config_server_main_form_submit_button').prop('disabled', true);
}

const SharedConfigHubForm = function (hub_id) {
    var form = document.getElementById('config_hub_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();
    document.getElementById(config_content_save_id).style.display='none';

    // Add new form
    $(config_content_id).append(form);
    $('#config_hub_main_form_submit_button').prop('disabled', true);
}

const SharedConfigSwitchForm = function (switch_id) {
    var form = document.getElementById('config_switch_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();
    document.getElementById(config_content_save_id).style.display='none';

    // Add new form
    $(config_content_id).append(form);
    $('#config_switch_main_form_submit_button').prop('disabled', true);
}

const SharedConfigEdgeForm = function (edge_id) {
    var form = document.getElementById('config_edge_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();
    document.getElementById(config_content_save_id).style.display='block';

    // Add new form
    $(config_content_id).append(form);
    $('#config_edge_main_form_submit_button').prop('disabled', true);
}


