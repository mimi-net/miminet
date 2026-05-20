const ConfigHostForm = function(host_id){
    var form = document.getElementById('config_host_main_form_script').innerHTML;
    var button = document.getElementById('config_host_save_script').innerHTML;
    var banner = document.getElementById('config_host_edit_banner_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();

    document.getElementById(config_content_save_id).style.display='block';

    // Add new form
    $(config_content_id).append(form);
    $(config_content_id).append(banner);
    $(config_content_save_tag).append(button);

    addIpFieldHandlers();

    // Set host_id
    $('#host_id').val(host_id);
    $('#net_guid').val(network_guid);

    function handleHostClick(event) {
        event.preventDefault();
        UpdateHostConfigurationForm(host_id);
    }

    $('#config_host_main_form_submit_button, #config_host_end_form').on('click', handleHostClick);

    // Update grid to exclude config panel area
    if (typeof updateGridForConfigPanel === 'function') {
        updateGridForConfigPanel();
    }
}

const ConfigRouterForm = function (router_id) {
    var form = document.getElementById('config_router_main_form_script').innerHTML;
    var button = document.getElementById('config_router_save_script').innerHTML;
    var banner = document.getElementById('config_router_edit_banner_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();

    document.getElementById(config_content_save_id).style.display='block';

    // Add new form
    $(config_content_id).append(form);
    $(config_content_id).append(banner);
    $(config_content_save_tag).append(button);

    addIpFieldHandlers();

    // Set host_id
    $('#router_id').val(router_id);
    $('#net_guid').val(network_guid);

    function handleRouterClick(event) {
        event.preventDefault();
        let data = $('#config_main_form').serialize();

        // Disable all input fields
        $("#config_main_form :input").prop("disabled", true);

        // Set loading spinner
        $('#config_router_main_form_submit_button').text('');
        $('#config_router_main_form_submit_button').append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

        // Use unified delete and save function
        DeleteAndSaveJob('router', UpdateRouterConfiguration, data, router_id);
    }

    $('#config_router_main_form_submit_button, #config_router_end_form').on('click', handleRouterClick);

    // Update grid to exclude config panel area
    if (typeof updateGridForConfigPanel === 'function') {
        updateGridForConfigPanel();
    }
}

const ConfigServerForm = function (server_id) {
    var form = document.getElementById('config_server_main_form_script').innerHTML;
    var button = document.getElementById('config_server_save_script').innerHTML;
    var banner = document.getElementById('config_server_edit_banner_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();

    document.getElementById(config_content_save_id).style.display='block';

    // Add new form
    $(config_content_id).append(form);
    $(config_content_id).append(banner);
    $(config_content_save_tag).append(button);

    addIpFieldHandlers();

    // Set host_id
    $('#server_id').val(server_id);
    $('#net_guid').val(network_guid);

    function handleServerClick(event) {
        event.preventDefault();
        let data = $('#config_main_form').serialize();

        // Disable all input fields
        $("#config_main_form :input").prop("disabled", true);

        // Set loading spinner
        $('#config_server_main_form_submit_button').text('');
        $('#config_server_main_form_submit_button').append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

        // Use unified delete and save function
        DeleteAndSaveJob('server', UpdateServerConfiguration, data, server_id);
    }

    $('#config_server_main_form_submit_button, #config_server_end_form').on('click', handleServerClick);

    // Update grid to exclude config panel area
    if (typeof updateGridForConfigPanel === 'function') {
        updateGridForConfigPanel();
    }
}

const ConfigHubForm = function (hub_id) {
    var form = document.getElementById('config_hub_main_form_script').innerHTML;
    var button = document.getElementById('config_hub_save_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();

    document.getElementById(config_content_save_id).style.display='block';

    // Add new form
    $(config_content_id).append(form);
    $(config_content_save_tag).append(button);

    addIpFieldHandlers();

    // Set host_id
    $('#hub_id').val(hub_id);
    $('#net_guid').val(network_guid);

    function handleHubClick(event) {
        event.preventDefault();
        let data = $('#config_hub_main_form').serialize();

        // Disable all input fields
        $("#config_hub_main_form :input").prop("disabled", true);

        // Set loading spinner
        $('#config_hub_main_form_submit_button').text('');
        $('#config_hub_main_form_submit_button').append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

        UpdateHubConfiguration(data, hub_id);
    }

    $('#config_hub_main_form_submit_button, #config_hub_end_form').on('click', handleHubClick);

    // Update grid to exclude config panel area
    if (typeof updateGridForConfigPanel === 'function') {
        updateGridForConfigPanel();
    }
}

const ConfigSwitchForm = function (switch_id) {
    var form = document.getElementById('config_switch_main_form_script').innerHTML;
    var button = document.getElementById('config_switch_save_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();

    document.getElementById(config_content_save_id).style.display='block';

    // Add new form
    $(config_content_id).append(form);
    $(config_content_save_tag).append(button);

    addIpFieldHandlers();

    // Add href for mimishark
    // var url = "/MimiShark?guid="+network_guid
    // $(needhref).attr('href',url)

    // Set host_id
    $('#switch_id').val(switch_id);
    $('#net_guid').val(network_guid);

    function handleSwitchClick(event) {
        $("#config_switch_main_form [name='config_rstp_stp']").val($('#config_button_rstp').val());
        event.preventDefault();
        let data = $('#config_switch_main_form').serialize();

        // Disable all input fields
        $("#config_switch_main_form :input").prop("disabled", true);

        // Set loading spinner
        $('#config_switch_main_form_submit_button').text('');
        $('#config_switch_main_form_submit_button').append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

        DeleteAndSaveJob('switch', UpdateSwitchConfiguration, data, switch_id);
    }

    $('#config_switch_main_form_submit_button, #config_switch_end_form').on('click', handleSwitchClick);

    // Update grid to exclude config panel area
    if (typeof updateGridForConfigPanel === 'function') {
        updateGridForConfigPanel();
    }
}

const ConfigEdgeForm = function (edge_id) {
    let edgeSaveXHR = null;
    var form = document.getElementById('config_edge_main_form_script').innerHTML;
    var button = document.getElementById('config_edge_save_script').innerHTML;


    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();

    document.getElementById(config_content_save_id).style.display='block';

    // Add new form
    $(config_content_id).append(form);
    $(config_content_save_tag).append(button);

    // Set host_id
    $('#edge_id').val(edge_id);
    $('#net_guid').val(network_guid);

    function handleEdgeClick(event) {
        event.preventDefault();

        if (edgeSaveXHR) {
            edgeSaveXHR.abort();
        }

        let data = $('#config_edge_main_form').serialize();
        const edge = edges.find(e => e.data.id === edge_id);
        console.log(edge);
        const lossValue = $("#edge_loss").val();
        const duplicateValue = $("#edge_duplicate").val();

        if (edge) {
            edge.data.loss_percentage = lossValue;
            edge.data.duplicate_percentage = duplicateValue;
        }
        const inputsToDisable = $('#edge_loss, #edge_duplicate, #config_edge_main_form_submit_button');
        inputsToDisable.prop("disabled", true);

        $('#config_edge_main_form_submit_button').html(
            '<span class="spinner-border spinner-border-sm" role="status"></span> Сохранение...'
        );

        edgeSaveXHR = UpdateEdgeConfiguration(data);
        inputsToDisable.prop("disabled", false);
    }

    $('#config_edge_main_form_submit_button, #config_edge_end_form').off('click').on('click', handleEdgeClick);

    // Update grid to exclude config panel area
    if (typeof updateGridForConfigPanel === 'function') {
        updateGridForConfigPanel();
    }
}

const ConfigHubName = function (hostname) {

    var text = document.getElementById('config_hub_name_script').innerHTML;

    $(config_hub_main_form_id).prepend((text));
    $('#config_hub_name').val(hostname);
}

const ConfigEdgeNetworkIssues = function (edge_loss, edge_duplicate) {
    var text = document.getElementById('config_edge_set_network_issues_script').innerHTML;
    $(config_edge_main_form_id).prepend(text);
    $('#edge_loss').val(edge_loss);
    $('#edge_duplicate').val(edge_duplicate);
};

const ConfigEdgeEndpoints = function (edge_source, edge_target) {

    var text = document.getElementById('config_edge_edpoint_script').innerHTML;

    $(config_edge_main_form_id).prepend((text));
    $('#edge_source').val(edge_source);
    $('#edge_target').val(edge_target);
}

const ConfigSwitchName = function (hostname) {

    var text = document.getElementById('config_switch_name_script').innerHTML;

    $(config_switch_main_form_id).prepend((text));
    $('#switch_name').val(hostname);
}

const ConfigSwtichSTP = function (stp) {
    var elem = document.getElementById('config_switch_checkbox_stp_script');

    $(elem.innerHTML).insertBefore('#config_switch_end_form');

    if (stp === 1) {
        $('#config_switch_stp').attr('checked', 'checked');
    }

    var warning_text = document.getElementById('config_switch_warning_stp_script').innerHTML;
    $('#config_switch_stp').on('click', function () {
        if ($(this).is(':checked')) {
            $(warning_text).insertBefore('#config_switch_end_form');
        } else {
            $('#config_warning_stp').remove();
        }
    });
}

const ConfigSwtichRSTP = function (rstp) {
    var elem = document.getElementById('config_switch_checkbox_rstp_script');

    $(elem.innerHTML).insertBefore('#config_switch_end_form');

    if (rstp === 1) {
        $('#config_switch_rstp').attr('checked', 'checked');
    }

    var warning_text = document.getElementById('config_switch_warning_rstp_script').innerHTML;
    $('#config_switch_rstp').on('click', function () {
        if ($(this).is(':checked')) {
            $(warning_text).insertBefore('#config_switch_end_form');
        } else {
            $('#config_warning_rstp').remove();
        }
    });
}

