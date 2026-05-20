$('#config_host').load(ExternalUrlFor("/config_host.html"));
$('#config_hub').load(ExternalUrlFor("/config_hub.html"));
$('#config_switch').load(ExternalUrlFor("/config_switch.html"));
$('#config_edge').load(ExternalUrlFor("/config_edge.html"));
$('#config_router').load(ExternalUrlFor("/config_router.html"));
$('#config_server').load(ExternalUrlFor("/config_server.html"));
$('#config_vlan').load(ExternalUrlFor("/config_vlan.html"));
$('#config_vxlan').load(ExternalUrlFor("/config_vxlan.html"));

const config_content_id = "#config_content";
const config_main_form_id = "#config_main_form";
const config_router_main_form_id = "#config_router_main_form";
const config_server_main_form_id = "#config_server_main_form";
const config_hub_main_form_id = "#config_hub_main_form";
const config_switch_main_form_id = "#config_switch_main_form";
const config_edge_main_form_id = "#config_edge_main_form";
const config_content_save_tag = "#config_content_save";
const config_content_save_id = "config_content_save";

const ClearConfigForm = function (text) {

    let txt = ''

    if (!text) {
        txt = 'Тут будут настройки устройств. Выделите любое на схеме.';
    }

    // Clear all child
    $(config_content_id).empty();
    $(config_content_save_tag).empty();
    $(config_content_id).append('<span>' + txt + '</span>');
    document.getElementById(config_content_save_id).style.display='none';

    // Update grid to reclaim full width
    if (typeof updateGridForConfigPanel === 'function') {
        updateGridForConfigPanel();
    }
}

const HostWarningMsg = function (msg) {

    let warning_msg = '<div class="alert alert-info alert-dismissible fade show" role="alert">' +
        msg + '<button class="btn-close" type="button" data-bs-dismiss="alert" aria-label="Close"></button></div>';

    $(config_content_id).prepend(warning_msg);
}
const SwitchWarningMsg = function (msg) {

    let warning_msg = '<div class="alert alert-info alert-dismissible fade show" role="alert">' +
        msg + '<button class="btn-close" type="button" data-bs-dismiss="alert" aria-label="Close"></button></div>';

    $(config_content_id).prepend(warning_msg);
}

const ServerWarningMsg = function (msg) {

    let warning_msg = '<div class="alert alert-info alert-dismissible fade show" role="alert">' +
        msg + '<button class="btn-close" type="button" data-bs-dismiss="alert" aria-label="Close"></button></div>';

    $(config_content_id).prepend(warning_msg);
}

const HostErrorMsg = function (msg) {

    $(config_content_id).find('.alert-info, .alert-danger').remove();

    let error_msg = '<div class="alert alert-info alert-dismissible fade show" role="alert">' +
        msg + '<button class="btn-close" type="button" data-bs-dismiss="alert" aria-label="Close"></button></div>';

    $(config_content_id).prepend(error_msg);

    $("#config_main_form :input").prop("disabled", false);
    $("#config_router_main_form :input").prop("disabled", false);
    $("#config_server_main_form :input").prop("disabled", false);
    $("config_switch_main_form :input").prop("disabled", false);

    $('#config_host_main_form_submit_button').text('Сохранить').removeClass('disabled');
    $('#config_router_main_form_submit_button').text('Сохранить').removeClass('disabled');
    $('#config_server_main_form_submit_button').text('Сохранить').removeClass('disabled');
    $('#config_switch_main_form_submit_button').text('Сохранить').removeClass('disabled');
}

const UpdateJobCounter = function (counterId, deviceId = null) {
    const counter = document.getElementById(counterId);
    if (!counter) {
        return;
    }

    counter.style.display = 'none';
}

const UpdateHostConfigurationForm = function(host_id) {
    let data = $('#config_main_form').serialize();

    // Disable all input fields
    $("#config_main_form :input").prop("disabled", true);

    // Set loading spinner
    $('#config_host_main_form_submit_button').text('');
    $('#config_host_main_form_submit_button').append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

    // Use unified delete and save function
    DeleteAndSaveJob('host', UpdateHostConfiguration, data, host_id);
};

