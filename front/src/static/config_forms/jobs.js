const UpdateHostForm = function(name) {
    elem = document.getElementById(name).innerHTML;
    host_job_list = document.getElementById('config_host_job_list');

    if (!elem || !host_job_list) {
        return;
    }

    $('div[name="config_host_select_input"]').remove();
    $(elem).insertBefore(host_job_list);
};

const ConfigHostJobOnChange = function (evnt) {

    let elem = null;
    let host_job_list = null;

    switch (evnt.target.value) {
        case '1':
            UpdateHostForm('config_host_ping_c_1_script');
            break;

        case '2':
            UpdateHostForm('config_host_ping_with_options_script');
            break;

        case '3':
            UpdateHostForm('config_host_send_udp_data_script');
            break;

        case '4':
            UpdateHostForm('config_host_send_tcp_data_script');
            break;

        case '5':
            UpdateHostForm('config_host_traceroute_with_options_script');
            break;

        case '102':
            UpdateHostForm('config_host_add_route_script');
            break;

        case '103':
            UpdateHostForm('config_host_add_arp_cache_script');
            break;
        
        case '108':
            UpdateHostForm('config_host_add_dhclient');
            FillDeviceSelectIntf('#config_host_add_dhclient_interface_select_iface_field', '#host_id', "Выберите линк", false)
            break;

        case '0':
            $('div[name="config_host_select_input"]').remove();
            break;

        default:
            console.log("Unknown target.value");
    }

}

const ConfigHostJob = function (host_jobs, shared = 0) {

    let elem = document.getElementById('config_host_job_script').innerHTML;
    let host_id = document.getElementById('host_id');

    if (!elem || !host_id) {
        return;
    }

    $(elem).insertBefore(host_id);

    // Set onchange
    document.getElementById('config_host_job_select_field').addEventListener('change', ConfigHostJobOnChange);

    // Update job counter with device ID
    UpdateJobCounter('config_host_job_counter', host_id.value);

    elem = document.getElementById('config_host_job_list_script').innerHTML;
    if (!elem) {
        return;
    }

    $(elem).insertBefore(host_id);

    // Print jobs if we have
    if (!host_jobs) {
        return;
    }

    $.each(host_jobs, function (i) {
        let jid = host_jobs[i].id;

        if (i == 0) {
            $('#config_host_job_list').append('<label class="text-sm">Команды</label>');
        }

        elem = document.getElementById('config_host_job_list_elem_script');

        if (!elem) {
            return;
        }

        let job_elem = jQuery.extend({}, elem);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_host_job_delete/g, 'config_host_job_delete_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_host_job_edit/g, 'config_host_job_edit_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/justify-content-between align-items-center\">/, 'justify-content-between align-items-center\"><small>' + host_jobs[i].print_cmd + '</small>');

        let text = job_elem.innerHTML;
        //$(text).insertBefore(host_id);
        $('#config_host_job_list').append(text);

        $('#config_host_job_delete_' + jid).click(function (event) {
            event.preventDefault();
            if (!shared) {
                DeleteJobFromHost(host_id.value, jid, network_guid);
            }
        });

        $('#config_host_job_edit_' + jid).click(function (event) {
            event.preventDefault();
            if (!shared) {
                EditJobInHost(host_id.value, jid, network_guid);
            }
        });
    });
}

const ConfigHostGateway = function (gw) {

    var text = document.getElementById('config_host_default_gw_script').innerHTML;

    $(text).insertBefore('#config_host_end_form');
    $('#config_host_default_gw').val(gw);
}

const ConfigRouterGateway = function (gw) {

    var text = document.getElementById('config_router_default_gw_script').innerHTML;

    $(text).insertBefore('#config_router_end_form');
    $('#config_router_default_gw').val(gw);
}

const ConfigServerGateway = function (gw) {

    var text = document.getElementById('config_server_default_gw_script').innerHTML;

    $(text).insertBefore('#config_server_end_form');
    $('#config_server_default_gw').val(gw);
}

const UpdateSwitchForm = function(name) {
    elem = document.getElementById(name).innerHTML;
    switch_job_list = document.getElementById('config_switch_job_list');

    if (!elem || !switch_job_list) {
        return;
    }

    $('div[name="config_switch_select_input"]').remove();
    $(elem).insertBefore(switch_job_list);
};

const ConfigSwitchJobOnChange = function(evnt) {
    switch (evnt.target.value) {
        case '0':
            $('div[name="config_switch_select_input"]').remove();

            break;
        case '6':
             UpdateSwitchForm('config_switch_link_down_script');
             FillDeviceSelectIntf("#config_switch_link_down_iface_select_field", '#switch_id', "Выберите линк", false);
            break;
        case '7':
            UpdateSwitchForm('config_switch_sleep_script');
    }
}
const ConfigSwitchJob = function (switch_jobs, shared = 0) {

    let elem = document.getElementById('config_switch_job_script').innerHTML;
    let switch_id = document.getElementById('switch_id');

    if (!elem || !switch_id) {
        return;
    }

    $(elem).insertBefore(switch_id);

    // Set onchange
    document.getElementById('config_switch_job_select_field').addEventListener('change', ConfigSwitchJobOnChange);

    // Update job counter with device ID
    UpdateJobCounter('config_switch_job_counter', switch_id.value);

    elem = document.getElementById('config_switch_job_list_script').innerHTML;
    if (!elem) {
        return;
    }

    $(elem).insertBefore(switch_id);

    // Print jobs if we have
    if (!switch_jobs) {
        return;
    }

    $.each(switch_jobs, function (i) {
        let jid = switch_jobs[i].id;

        if (i == 0) {
            $('#config_switch_job_list').append('<label class="text-sm">Команды</label>');
        }

        elem = document.getElementById('config_switch_job_list_elem_script');

        if (!elem) {
            return;
        }

        let job_elem = jQuery.extend({}, elem);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_switch_job_delete/g, 'config_switch_job_delete_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_switch_job_edit/g, 'config_switch_job_edit_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/justify-content-between align-items-center\">/, 'justify-content-between align-items-center\"><small>' + switch_jobs[i].print_cmd + '</small>');

        let text = job_elem.innerHTML;
        //$(text).insertBefore(host_id);
        $('#config_switch_job_list').append(text);

        $('#config_switch_job_delete_' + jid).click(function (event) {
            event.preventDefault();
            if (!shared) {
                DeleteJobFromSwitch(switch_id.value, jid, network_guid);
            }
        });

        $('#config_switch_job_edit_' + jid).click(function (event) {
            event.preventDefault();
            if (!shared) {
                EditJobInSwitch(switch_id.value, jid, network_guid);
            }
        });
    });
}

const ConfigRouterJobOnChange = function(evnt) {

    switch (evnt.target.value) {
        case '0':
            $('div[name="config_router_select_input"]').remove();

            break;
        case '1':
            UpdateRouterForm('config_router_ping_c_1_script');

            break;
        case '100':
            UpdateRouterForm('config_router_add_ip_mask_script');
            FillDeviceSelectIntf("#config_router_add_ip_mask_iface_select_field", '#router_id', "Выберите линк", false);
        
            break;
        case '101':
            UpdateRouterForm('config_router_add_nat_masquerade_script');
            FillDeviceSelectIntf("#config_router_add_nat_masquerade_iface_select_field", '#router_id', "Выберите линк", false);

            break;
        case '102':
            UpdateRouterForm('config_router_add_route_script');

            break;
        case '104':
            UpdateRouterForm('config_router_add_subinterface_script');
            FillDeviceSelectIntf("#config_router_add_subinterface_iface_select_field", '#router_id', "Выберите линк" ,false);

            break;
        case '105':
            UpdateRouterForm('config_router_add_ipip_tunnel_script');
            FillDeviceSelectIntf("#config_router_add_ipip_tunnel_iface_select_ip_field", '#router_id');

            break;
        case '106':
            UpdateRouterForm('config_router_add_gre_interface_script');
            FillDeviceSelectIntf("#config_router_add_gre_interface_select_ip_field", '#router_id');

            break;
        case '107':
            UpdateRouterForm('config_router_add_arp_proxy_script');
            FillDeviceSelectIntf("#config_router_add_arp_proxy_iface_select_field", '#router_id', "Выберите линк", false);
        case '109':
            UpdateRouterForm('config_router_add_port_forwarding_tcp_script');
            FillDeviceSelectIntf("#config_router_add_port_forwarding_tcp_iface_select_field", "#router_id", "Выберите линк", false)
            break;
        case '110':
            UpdateRouterForm('config_router_add_port_forwarding_udp_script');
            FillDeviceSelectIntf("#config_router_add_port_forwarding_udp_iface_select_field", "#router_id", "Выберите линк", false)
            break;
        default:
            console.log("Unknown target.value");
    }
}

const ConfigRouterJob = function (router_jobs, shared = 0) {

    let elem = document.getElementById('config_router_job_script').innerHTML;
    let router_id = document.getElementById('router_id');

    if (!elem || !router_id) {
        return;
    }

    $(elem).insertBefore(router_id);

    // Set onchange
    document.getElementById('config_router_job_select_field').addEventListener('change', ConfigRouterJobOnChange);

    // Update job counter with device ID
    UpdateJobCounter('config_router_job_counter', router_id.value);

    elem = document.getElementById('config_router_job_list_script').innerHTML;
    if (!elem) {
        return;
    }

    $(elem).insertBefore(router_id);

    // Print jobs if we have
    if (!router_jobs) {
        return;
    }

    $.each(router_jobs, function (i) {
        let jid = router_jobs[i].id;

        if (i == 0) {
            $('#config_router_job_list').append('<label class="text-sm">Команды</label>');
        }

        elem = document.getElementById('config_router_job_list_elem_script');

        if (!elem) {
            return;
        }

        let job_elem = jQuery.extend({}, elem);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_router_job_delete/g, 'config_router_job_delete_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_router_job_edit/g, 'config_router_job_edit_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/justify-content-between align-items-center\">/, 'justify-content-between align-items-center\"><small>' + router_jobs[i].print_cmd + '</small>');

        let text = job_elem.innerHTML;
        //$(text).insertBefore(host_id);
        $('#config_router_job_list').append(text);

        $('#config_router_job_delete_' + jid).click(function (event) {
            event.preventDefault();
            if (!shared) {
                DeleteJobFromRouter(router_id.value, jid, network_guid);
            }
        });

        $('#config_router_job_edit_' + jid).click(function (event) {
            event.preventDefault();
            if (!shared) {
                EditJobInRouter(router_id.value, jid, network_guid);
            }
        });
    });
}

const ConfigServerJob = function (server_jobs, shared = 0) {

    let elem = document.getElementById('config_server_job_script').innerHTML;
    let server_id = document.getElementById('server_id');

    if (!elem || !server_id) {
        return;
    }

    $(elem).insertBefore(server_id);

    // Set onchange
    document.getElementById('config_server_job_select_field').addEventListener('change', ConfigServerJobOnChange);

    // Update job counter with device ID
    UpdateJobCounter('config_server_job_counter', server_id.value);

    elem = document.getElementById('config_server_job_list_script').innerHTML;
    if (!elem) {
        return;
    }

    $(elem).insertBefore(server_id);

    // Print jobs if we have
    if (!server_jobs) {
        return;
    }

    $.each(server_jobs, function (i) {
        let jid = server_jobs[i].id;

        if (i == 0) {
            $('#config_server_job_list').append('<label class="text-sm">Команды</label>');
        }

        elem = document.getElementById('config_server_job_list_elem_script');

        if (!elem) {
            return;
        }

        let job_elem = jQuery.extend({}, elem);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_server_job_delete/g, 'config_server_job_delete_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/config_server_job_edit/g, 'config_server_job_edit_' + jid);
        job_elem.innerHTML = job_elem.innerHTML.replace(/justify-content-between align-items-center\">/, 'justify-content-between align-items-center\"><small>' + server_jobs[i].print_cmd + '</small>');

        let text = job_elem.innerHTML;
        //$(text).insertBefore(host_id);
        $('#config_server_job_list').append(text);

        $('#config_server_job_delete_' + jid).click(function (event) {
            event.preventDefault();

            if (!shared) {
                DeleteJobFromServer(server_id.value, jid, network_guid);
            }

        });

        $('#config_server_job_edit_' + jid).click(function (event) {
            event.preventDefault();
            if (!shared) {
                EditJobInServer(server_id.value, jid, network_guid);
            }
        });
    });
}

const UpdateServerForm = function(name) {
    elem = document.getElementById(name).innerHTML;
    server_job_list = document.getElementById('config_server_job_list');

    if (!elem || !server_job_list) {
        return;
    }

    $('div[name="config_server_select_input"]').remove();
    $(elem).insertBefore(server_job_list);
}

const ConfigServerJobOnChange = function (evnt) {

    let elem = null;
    let server_job_list = null;
    let n = null;
    let server_id = null;

    switch (evnt.target.value) {
        case '0':
            $('div[name="config_server_select_input"]').remove();
            break;

        case '1':
            UpdateServerForm('config_server_ping_c_1_script');
            break;

        case '200':
            UpdateServerForm('config_server_start_udp_server_script');
            break;

        case '201':
            UpdateServerForm('config_server_start_tcp_server_script');
            break;

        case '202':
            UpdateServerForm('config_server_block_tcp_udp_port_script');
            break;
        
        case '203':
            UpdateServerForm('config_server_add_dhcp_server_script');
            FillDeviceSelectIntf('#config_server_add_dhcp_interface_select_iface_field', '#server_id', "Выберите линк", false)
            break;

        default:
            console.log("Unknown target.value");
    }

}

const DisableFormInputs = function () {
    let s = config_content_id + ' :input';
    $(s).prop("disabled", true);
    $(config_content_save_tag + ' :input').prop("disabled", true);
}

const DisableVLANInputs = function (n) {
    var modalId = 'VlanModal_' + n.data.id;

    $(document).ready(function () {
        $('#config_button_vlan').prop('disabled', false);
        $('#' + modalId + ' :input').not('.btn-close').prop('disabled', true);
        $('#' + modalId + ' .form-check-input, ' + modalId + ' .form-switch input').prop('disabled', true);
    });
};

const UpdateRouterForm = function(name) {
    /**
     * Replace old form with new one
     */
    elem = document.getElementById(name).innerHTML;
    router_job_list = document.getElementById('config_router_job_list');

    if (!elem || !router_job_list){
        return;
    }

    $('div[name="config_router_select_input"]').remove();
    $(elem).insertBefore(router_job_list);
}

const FillDeviceSelectIntf = function(select_id, device, field_msg = 'Интерфейс начальной точки', return_ip = true) {
    /**
    * Fill select element with network hosts.
    * @param  {String} select_id ID(name) of the element to which you need to add data.
    * @param  {String} field_msg Message that will be displayed in the select list by default.
    * @param  {Boolean} return_ip True if replace user's input with ip and False if replace it with element's id.
   */

    // configured router id
    device_id = $(device)[0].value;

    if (!device_id) {
        console.log("Не нашел device_id");
        return
    }

    device_node = nodes.find(n => n.data.id === device_id);
    device_type = device.slice(1, -3 ) //example : #router_id  -> router
    
    if (!device_node) {
        console.log("Не нашел device_node");
        return;
    }

    if (!device_node.interface.length) {
        $(select_id).append('<option selected value="0">Мало интерфейсов</option>');
        return;
    } else {
        $(select_id).append(`<option selected value="0">${field_msg}</option>`);
    }
    $(select_id).on('change', function () {
        let selectedOption = $(this).find('option:selected'); // Получаем выбранный элемент
        let selectedLabel = selectedOption.text(); // Получаем текст выбранного элемента
        document.getElementById(device_type + '_connection_host_label_hidden').value = selectedLabel; // Записываем его в скрытое поле
    });

    device_node.interface.forEach(function(iface) {
        // iterating over the router interfaces

        let iface_id = iface.id;
        let iface_ip = iface.ip;

        if (!iface_id || (return_ip && !iface_ip)) {
            console.log("Не нашел ip/id у интерфейса");
            return;
        }

        let connect_id = iface.connect;
        if (!connect_id) {
            console.log("Не нашел подключение у интерфейса");
            return;
        }

        let edge = edges.find(e => e.data.id === connect_id);

        if (!edge) {
            console.log("Не нашел ребро по подключению интерфейса");
            return;
        }

        let edge_source = edge.data.source;
        let edge_target = edge.data.target;

        if (!edge_source || !edge_target) {
            console.log("Не получилось найти target и source у ребра");
            return;
        }

        let device_connection = (device_node.data.id === edge_target) ? edge_source : edge_target;

        let device_connection_host_node = nodes.find(n => n.data.id === device_connection);
        let device_connection_host_label = (device_connection_host_node) ? device_connection_host_node.data.label : "Unknown";

        $(select_id).append('<option value="' + (return_ip ? iface_ip : iface_id) + '">' + device_connection_host_label + '</option>');

    });
}


const DisableVXLANInputs = function (n) {
    var modalId = 'VxlanConfigModal' + n.data.id;


    $(document).ready(function () {
        $('#config_button_vxlan').prop('disabled', false);
        $('#' + modalId + ' :input').not('.btn-close').prop('disabled', true);
        $('#' + modalId + ' .form-check-input, #' + modalId + ' .form-switch input').prop('disabled', true);
        $('<style>')
            .prop('type', 'text/css')
            .html(`
        .network-interface .btn-danger,
        .client-interface .btn-danger {
            display: none !important;
        }
    `)
            .appendTo('head');

        $('#' + modalId).off('hidden.bs.modal.myNamespace');
    });
};

// ========== DEVICE-SPECIFIC COMMAND EDITING ==========

/// Edit job in host
