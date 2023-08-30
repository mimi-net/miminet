$('#config_host').load( "config_host.html" );
$('#config_hub').load( "config_hub.html" );
$('#config_switch').load( "config_switch.html" );
$('#config_edge').load( "config_edge.html" );
$('#config_router').load( "config_router.html" );
$('#config_server').load( "config_server.html" );

const config_content_id = "#config_content";
const config_main_form_id = "#config_main_form";
const config_router_main_form_id = "#config_router_main_form";
const config_server_main_form_id = "#config_server_main_form";
const config_hub_main_form_id = "#config_hub_main_form";
const config_switch_main_form_id = "#config_switch_main_form";
const config_edge_main_form_id = "#config_edge_main_form";

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

const HostWarningMsg = function(msg){

    let warning_msg = '<div class="alert alert-info alert-dismissible fade show" role="alert">' +
    msg + '<button class="btn-close" type="button" data-bs-dismiss="alert" aria-label="Close"></button></div>';

    $(config_content_id).prepend(warning_msg);
}

const ServerWarningMsg = function(msg){

    let warning_msg = '<div class="alert alert-info alert-dismissible fade show" role="alert">' +
    msg + '<button class="btn-close" type="button" data-bs-dismiss="alert" aria-label="Close"></button></div>';

    $(config_content_id).prepend(warning_msg);
}

const ConfigHostForm = function(host_id){
    let form = document.getElementById('config_main_form_script').innerHTML;

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

const ConfigRouterForm = function(router_id){
    let form = document.getElementById('config_router_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#router_id').val( router_id );
    $('#net_guid').val( network_guid );

    $('#config_router_main_form_submit_button').click(function(event) {
        event.preventDefault();
        let data = $('#config_main_form').serialize();

        // Disable all input fields
        $("#config_main_form :input").prop("disabled", true);

        // Set loading spinner
        $(this).text('');
        $(this).append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

        UpdateRouterConfiguration(data, router_id);
    });
}

const ConfigServerForm = function(server_id){
    let form = document.getElementById('config_server_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#server_id').val( server_id );
    $('#net_guid').val( network_guid );

    $('#config_server_main_form_submit_button').click(function(event) {
        event.preventDefault();
        let data = $('#config_main_form').serialize();

        // Disable all input fields
        $("#config_main_form :input").prop("disabled", true);

        // Set loading spinner
        $(this).text('');
        $(this).append('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span><span class="ps-3">Сохранение...</span>');

        UpdateServerConfiguration(data, server_id);
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

    // Add href for mimishark
    // var url = "/MimiShark?guid="+network_guid
    // $(needhref).attr('href',url)

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

const ConfigEdgeForm = function(edge_id){

    var form = document.getElementById('config_edge_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#edge_id').val( edge_id );
    $('#net_guid').val( network_guid );
}

const ConfigEdgeEndpoints = function(edge_source, edge_target){

    var text = document.getElementById('config_edge_edpoint_script').innerHTML;

    $(config_edge_main_form_id).prepend((text));
    $('#edge_source').val(edge_source);
    $('#edge_target').val(edge_target);
}

const ConfigSwitchName = function(hostname){

    var text = document.getElementById('config_switch_name_script').innerHTML;

    $(config_switch_main_form_id).prepend((text));
    $('#config_switch_name').val(hostname);
}

const ConfigSwtichSTP = function(stp){
    var elem = document.getElementById('config_switch_checkbox_stp_script');

    $(elem.innerHTML).insertBefore('#config_switch_main_form_submit_button');

    if (stp === 1) {
        $('#config_switch_stp').attr('checked', 'checked');
    }

    var warning_text = document.getElementById('config_switch_warning_stp_script').innerHTML;
    $('#config_switch_stp').on('click', function(){
        if ($(this).is(':checked')){
            $(warning_text).insertBefore('#config_switch_main_form_submit_button');
        } else {
            $('#config_warning_stp').remove();
        }
    }); 
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

const SharedConfigRouterForm = function(router_id){
    var form = document.getElementById('config_router_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#router_id').val( router_id );
    $('#net_guid').val( network_guid );

    $('#config_router_main_form_submit_button').prop('disabled', true);
}

const SharedConfigServerForm = function(router_id){
    var form = document.getElementById('config_server_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#router_id').val( router_id );
    $('#net_guid').val( network_guid );

    $('#config_server_main_form_submit_button').prop('disabled', true);
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

const ConfigRouterName = function(hostname){

    var text = document.getElementById('config_router_name_script').innerHTML;

    $(config_main_form_id).prepend((text));
    $('#config_router_name').val(hostname);
}

const ConfigServerName = function(hostname){

    var text = document.getElementById('config_server_name_script').innerHTML;

    $(config_main_form_id).prepend((text));
    $('#config_server_name').val(hostname);
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

    if (pcaps.includes(name)){
        $('#config_host_iface_name_label_' + name).html('Линк к (<a href="/host/mimishark?guid='+network_guid+'&iface='+name +'" target="_blank">pcap</a>)');
    }
}

const ConfigRouterInterface = function(name, ip, netmask, connected_to){

    let elem = document.getElementById('config_router_interface_script');
    let eth = jQuery.extend({}, elem);

    if (!name){
        return;
    }

    eth.innerHTML = eth.innerHTML.replace(/config_router_iface_name_label_example/g, 'config_router_iface_name_label_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_router_iface_name_example/g, 'config_router_iface_name_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_router_ip_example/g, 'config_router_ip_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_router_mask_example/g, 'config_router_mask_' + name);

    var text = eth.innerHTML;

    $(text).insertBefore('#config_router_main_form_submit_button');
    $('<input type="hidden" name="config_router_iface_ids[]" value="' + name + '"/>').insertBefore('#config_router_iface_name_' + name);
    $('#config_router_iface_name_' + name).attr("placeholder", connected_to);
    $('#config_router_ip_' + name).val(ip);
    $('#config_router_mask_' + name).val(netmask);
}

const ConfigServerInterface = function(name, ip, netmask, connected_to){

    let elem = document.getElementById('config_server_interface_script');
    let eth = jQuery.extend({}, elem);

    if (!name){
        return;
    }

    eth.innerHTML = eth.innerHTML.replace(/config_server_iface_name_label_example/g, 'config_server_iface_name_label_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_server_iface_name_example/g, 'config_server_iface_name_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_server_ip_example/g, 'config_server_ip_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_server_mask_example/g, 'config_server_mask_' + name);

    var text = eth.innerHTML;

    $(text).insertBefore('#config_server_main_form_submit_button');
    $('<input type="hidden" name="config_server_iface_ids[]" value="' + name + '"/>').insertBefore('#config_server_iface_name_' + name);
    $('#config_server_iface_name_' + name).attr("placeholder", connected_to);
    $('#config_server_ip_' + name).val(ip);
    $('#config_server_mask_' + name).val(netmask);

    if (pcaps.includes(name)){
        $('#config_server_iface_name_label_' + name).html('Линк к (<a href="/host/mimishark?guid='+network_guid+'&iface='+name +'" target="_blank">pcap</a>)');
    }
}

const ConfigHostJobOnChange = function(evnt){

    let elem = null;
    let host_job_list = null;

    switch(evnt.target.value)
    {
        case '1':
            elem = document.getElementById('config_host_ping_c_1_script').innerHTML;
            host_job_list = document.getElementById('config_host_job_list');

            if (!elem || !host_job_list){
                return;
            }

            $('div[name="config_host_select_input"]').remove();
            $(elem).insertBefore(host_job_list);
            break;

        case '2':
            elem = document.getElementById('config_host_ping_with_options_script').innerHTML;
            host_job_list = document.getElementById('config_host_job_list');

            if (!elem || !host_job_list){
                return;
            }

            $('div[name="config_host_select_input"]').remove();
            $(elem).insertBefore(host_job_list);
            break;

        case '3':
            elem = document.getElementById('config_host_send_udp_data_script').innerHTML;
            host_job_list = document.getElementById('config_host_job_list');

            if (!elem || !host_job_list){
                return;
            }

            $('div[name="config_host_select_input"]').remove();
            $(elem).insertBefore(host_job_list);
            break;

        case '4':
            elem = document.getElementById('config_host_send_tcp_data_script').innerHTML;
            host_job_list = document.getElementById('config_host_job_list');

            if (!elem || !host_job_list){
                return;
            }

            $('div[name="config_host_select_input"]').remove();
            $(elem).insertBefore(host_job_list);
            break;

        case '5':
            elem = document.getElementById('config_host_traceroute_with_options_script').innerHTML;
            host_job_list = document.getElementById('config_host_job_list');

            if (!elem || !host_job_list){
                return;
            }

            $('div[name="config_host_select_input"]').remove();
            $(elem).insertBefore(host_job_list);
            break;

        case '102':
            elem = document.getElementById('config_host_add_route_script').innerHTML;
            host_job_list = document.getElementById('config_host_job_list');

            if (!elem || !host_job_list){
                return;
            }

            $('div[name="config_host_select_input"]').remove();
            $(elem).insertBefore(host_job_list);
            break;

        case '103':
            elem = document.getElementById('config_host_add_arp_cache_script').innerHTML;
            host_job_list = document.getElementById('config_host_job_list');

            if (!elem || !host_job_list){
                return;
            }

            $('div[name="config_host_select_input"]').remove();
            $(elem).insertBefore(host_job_list);
            break;

        case '0':
            $('div[name="config_host_select_input"]').remove();
            break;

        default:
            console.log("Unknown target.value");
    }

}

const ConfigHostJob = function(host_jobs, shared=0)
{

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
            if (!shared){
                DeleteJobFromHost(host_id.value, jid, network_guid);
            }
        });

    });
}

const ConfigHostGateway = function(gw){

    var text = document.getElementById('config_host_default_gw_script').innerHTML;

    $(text).insertBefore('#config_main_form_submit_button');
    $('#config_host_default_gw').val(gw);
}

const ConfigRouterGateway = function(gw){

    var text = document.getElementById('config_router_default_gw_script').innerHTML;

    $(text).insertBefore('#config_router_main_form_submit_button');
    $('#config_router_default_gw').val(gw);
}

const ConfigServerGateway = function(gw){

    var text = document.getElementById('config_server_default_gw_script').innerHTML;

    $(text).insertBefore('#config_server_main_form_submit_button');
    $('#config_server_default_gw').val(gw);
}

const ConfigRouterJobOnChange = function(evnt){

    let elem = null;
    let router_job_list = null;
    let n = null;
    let router_id = null;

    switch(evnt.target.value)
    {
        case '0':
            $('div[name="config_router_select_input"]').remove();
            break;

        case '1':
            elem = document.getElementById('config_router_ping_c_1_script').innerHTML;
            router_job_list = document.getElementById('config_router_job_list');

            if (!elem || !router_job_list){
                return;
            }

            $('div[name="config_router_select_input"]').remove();
            $(elem).insertBefore(router_job_list);
            break;

        case '100':
            elem = document.getElementById('config_router_add_ip_mask_script').innerHTML;
            router_job_list = document.getElementById('config_router_job_list');

            if (!elem || !router_job_list){
                console.log("config_router_add_ip_mask_script или config_router_job_list не найден.");
                return;
            }

            $('div[name="config_router_select_input"]').remove();
            $(elem).insertBefore(router_job_list);

            router_id = $('#router_id')[0].value;
            if (!router_id){
                console.log("Не нашел router_id");
                return
            }

            n = nodes.find(n => n.data.id === router_id);

            if (!n) {
                return;
            }

            if(!n.interface.length){
                console.log("Интерфейсов нет, нечего настраивать");
                return;
            }

            if(n.interface.length !== 1){
                $('#config_router_add_ip_mask_iface_select_field').append('<option selected value="0">Выберите линк</option>');
            }

            $.each(n.interface, function (i) {
                let iface_id = n.interface[i].id;

                if (!iface_id){
                    return;
                }

                let connect_id = n.interface[i].connect;
                if (!connect_id){
                    return;
                }

                let edge = edges.find(e => e.data.id === connect_id);

                if (!edge){
                    return;
                }

                let source_host = edge.data.source;
                let target_host = edge.data.target;

                if (!source_host || !target_host){
                    return;
                }

                let connected_to = target_host;

                if (n.data.id === target_host){
                    connected_to = source_host;
                }

                let connected_to_host = nodes.find(n => n.data.id === connected_to);
                let connected_to_host_label = "Unknown";

                if (connected_to_host){
                    connected_to_host_label = connected_to_host.data.label;
                }

                $('#config_router_add_ip_mask_iface_select_field').append('<option value="' + iface_id  + '">' + connected_to_host_label + '</option>');

            });
            break;

        case '101':
            elem = document.getElementById('config_router_add_nat_masquerade_script').innerHTML;
            router_job_list = document.getElementById('config_router_job_list');

            if (!elem || !router_job_list){
                return;
            }

            $('div[name="config_router_select_input"]').remove();
            $(elem).insertBefore(router_job_list);

            router_id = $('#router_id')[0].value;
            if (!router_id){
                console.log("Не нашел router_id");
                return
            }

            n = nodes.find(n => n.data.id === router_id);

            if (!n) {
                return;
            }

            if(!n.interface.length){
                console.log("Нет интерфейсов, нечего настраивать.");
                return;
            }

            if(n.interface.length === 1){
                $('#config_router_add_nat_masquerade_iface_select_field').append('<option selected value="0">Мало интерфейсов</option>');
                return;
            }

            $('#config_router_add_nat_masquerade_iface_select_field').append('<option selected value="0">Выберите линк</option>');

            $.each(n.interface, function (i) {
                let iface_id = n.interface[i].id;

                if (!iface_id){
                    return;
                }

                let connect_id = n.interface[i].connect;
                if (!connect_id){
                    return;
                }

                let edge = edges.find(e => e.data.id === connect_id);

                if (!edge){
                    return;
                }

                let source_host = edge.data.source;
                let target_host = edge.data.target;

                if (!source_host || !target_host){
                    return;
                }

                let connected_to = target_host;

                if (n.data.id === target_host){
                    connected_to = source_host;
                }

                let connected_to_host = nodes.find(n => n.data.id === connected_to);
                let connected_to_host_label = "Unknown";

                if (connected_to_host){
                    connected_to_host_label = connected_to_host.data.label;
                }

                $('#config_router_add_nat_masquerade_iface_select_field').append('<option value="' + iface_id  + '">' + connected_to_host_label + '</option>');

            });
            break;

        case '102':
            elem = document.getElementById('config_router_add_route_script').innerHTML;
            router_job_list = document.getElementById('config_router_job_list');

            if (!elem || !router_job_list){
                return;
            }

            $('div[name="config_router_select_input"]').remove();
            $(elem).insertBefore(router_job_list);
            break;

        default:
            console.log("Unknown target.value");
    }

}

const ConfigRouterJob = function(router_jobs, shared=0)
{

    let elem = document.getElementById('config_router_job_script').innerHTML;
    let router_id = document.getElementById('router_id');

    if (!elem || !router_id){
        return;
    }

    $(elem).insertBefore(router_id);

    // Set onchange
    document.getElementById('config_router_job_select_field').addEventListener('change', ConfigRouterJobOnChange);

    elem = document.getElementById('config_router_job_list_script').innerHTML;
    if (!elem){
        return;
    }

    $(elem).insertBefore(router_id);

    // Print jobs if we have
    if (!router_jobs)
    {
        return;
    }

    $.each(router_jobs, function (i) {
        let jid = router_jobs[i].id;

        if (i == 0){
            $('#config_router_job_list').append('<label class="text-sm">Команды</label>');
        }

        elem = document.getElementById('config_router_job_list_elem_script');

        if (!elem){
            return;
        }

        let job_elem = jQuery.extend({}, elem);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_router_job_delete/g, 'config_router_job_delete_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/justify-content-between align-items-center\">/, 'justify-content-between align-items-center\"><small>' + router_jobs[i].print_cmd + '</small>');

        let text = job_elem.innerHTML;
        //$(text).insertBefore(host_id);
        $('#config_router_job_list').append(text);

        $('#config_router_job_delete_' + jid).click(function(event) {
            event.preventDefault();
            if (!shared){
                DeleteJobFromRouter(router_id.value, jid, network_guid);
            }
        });
    });
}

const ConfigServerJob = function(server_jobs, shared = 0)
{

    let elem = document.getElementById('config_server_job_script').innerHTML;
    let server_id = document.getElementById('server_id');

    if (!elem || !server_id){
        return;
    }

    $(elem).insertBefore(server_id);

    // Set onchange
    document.getElementById('config_server_job_select_field').addEventListener('change', ConfigServerJobOnChange);

    elem = document.getElementById('config_server_job_list_script').innerHTML;
    if (!elem){
        return;
    }

    $(elem).insertBefore(server_id);

    // Print jobs if we have
    if (!server_jobs)
    {
        return;
    }

    $.each(server_jobs, function (i) {
        let jid = server_jobs[i].id;

        if (i == 0){
            $('#config_server_job_list').append('<label class="text-sm">Команды</label>');
        }

        elem = document.getElementById('config_server_job_list_elem_script');

        if (!elem){
            return;
        }

        let job_elem = jQuery.extend({}, elem);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_server_job_delete/g, 'config_server_job_delete_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/justify-content-between align-items-center\">/, 'justify-content-between align-items-center\"><small>' + server_jobs[i].print_cmd + '</small>');

        let text = job_elem.innerHTML;
        //$(text).insertBefore(host_id);
        $('#config_server_job_list').append(text);

        $('#config_server_job_delete_' + jid).click(function(event) {
            event.preventDefault();

            if (!shared){
                DeleteJobFromServer(server_id.value, jid, network_guid);
            }

        });
    });
}

const ConfigServerJobOnChange = function(evnt){

    let elem = null;
    let server_job_list = null;
    let n = null;
    let server_id = null;

    switch(evnt.target.value)
    {
        case '0':
            $('div[name="config_server_select_input"]').remove();
            break;

        case '1':
            elem = document.getElementById('config_server_ping_c_1_script').innerHTML;
            server_job_list = document.getElementById('config_server_job_list');

            if (!elem || !server_job_list){
                return;
            }

            $('div[name="config_server_select_input"]').remove();
            $(elem).insertBefore(server_job_list);
            break;

        case '200':
            elem = document.getElementById('config_server_start_udp_server_script').innerHTML;
            server_job_list = document.getElementById('config_server_job_list');

            if (!elem || !server_job_list){
                return;
            }

            $('div[name="config_server_select_input"]').remove();
            $(elem).insertBefore(server_job_list);
            break;

        case '201':
            elem = document.getElementById('config_server_start_tcp_server_script').innerHTML;
            server_job_list = document.getElementById('config_server_job_list');

            if (!elem || !server_job_list){
                return;
            }

            $('div[name="config_server_select_input"]').remove();
            $(elem).insertBefore(server_job_list);
            break;

        case '202':
            elem = document.getElementById('config_server_block_tcp_udp_port_script').innerHTML;
            server_job_list = document.getElementById('config_server_job_list');

            if (!elem || !server_job_list){
                return;
            }

            $('div[name="config_server_select_input"]').remove();
            $(elem).insertBefore(server_job_list);
            break;

        default:
            console.log("Unknown target.value");
    }

}

const DisableFormInputs = function(){
    let s = config_content_id + ' :input';
    $(s).prop("disabled", true);
}