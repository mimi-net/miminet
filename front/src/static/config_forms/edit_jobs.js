const EditJobInHost = function(host_id, job_id, network_guid) {
    const job = jobs.find(j => j.id === job_id);

    if (!job) {
        console.error('Job not found:', job_id);
        return;
    }

    EnterEditMode('host', job_id, job.job_id);

    // Set the select field to the job type
    const selectField = document.getElementById('config_host_job_select_field');
    if (selectField) {
        selectField.value = job.job_id.toString();

        // Trigger change event to show the form
        const event = new Event('change');
        selectField.dispatchEvent(event);

        // Fill in the form fields with job data
        setTimeout(() => {
            switch(job.job_id.toString()) {
                case '1': // ping (1 пакет)
                    $('#config_host_ping_c_1_ip').val(job.arg_1 || '');
                    break;
                case '2': // ping (с опциями)
                    $('#config_host_ping_with_options_options_input_field').val(job.arg_1 || '');
                    $('#config_host_ping_with_options_ip_input_field').val(job.arg_2 || '');
                    break;
                case '5': // traceroute (с опциями)
                    $('#config_host_traceroute_with_options_options_input_field').val(job.arg_1 || '');
                    $('#config_host_traceroute_with_options_ip_input_field').val(job.arg_2 || '');
                    break;
                case '3': // Отправить данные (UDP)
                    $('#config_host_send_udp_data_size_input_field').val(job.arg_1 || '');
                    $('#config_host_send_udp_data_ip_input_field').val(job.arg_2 || '');
                    $('#config_host_send_udp_data_port_input_field').val(job.arg_3 || '');
                    break;
                case '4': // Отправить данные (TCP)
                    $('#config_host_send_tcp_data_size_input_field').val(job.arg_1 || '');
                    $('#config_host_send_tcp_data_ip_input_field').val(job.arg_2 || '');
                    $('#config_host_send_tcp_data_port_input_field').val(job.arg_3 || '');
                    break;
                case '102': // Добавить маршрут
                    $('#config_host_add_route_ip_input_field').val(job.arg_1 || '');
                    $('#config_host_add_route_mask_input_field').val(job.arg_2 || '0');
                    $('#config_host_add_route_gw_input_field').val(job.arg_3 || '');
                    break;
                case '103': // Добавить запись в ARP-cache
                    $('#config_host_add_arp_cache_ip_input_field').val(job.arg_1 || '');
                    $('#config_host_add_arp_cache_mac_input_field').val(job.arg_2 || '');
                    break;
                case '108': // Запросить IP адрес автоматически
                    // No parameters needed - DHCP client request
                    break;
            }
        }, 200);
    }
};

// Edit job in router
const EditJobInRouter = function(router_id, job_id, network_guid) {
    const job = jobs.find(j => j.id === job_id);

    if (!job) {
        console.error('Job not found:', job_id);
        return;
    }

    EnterEditMode('router', job_id, job.job_id);

    // Set the select field to the job type
    const selectField = document.getElementById('config_router_job_select_field');
    if (selectField) {
        selectField.value = job.job_id.toString();

        // Trigger change event to show the form
        const event = new Event('change');
        selectField.dispatchEvent(event);

        // Fill in the form fields with job data
        setTimeout(() => {
            switch(job.job_id.toString()) {
            case '1': // ping (1 пакет)
                UpdateRouterForm('config_router_ping_c_1_script');
                $('#config_router_ping_c_1_ip').val(job.arg_1 || '');
                break;
            case '100': // Добавить IP адрес
                UpdateRouterForm('config_router_add_ip_mask_script');
                FillDeviceSelectIntf("#config_router_add_ip_mask_iface_select_field", '#router_id', "Выберите линк", false);
                $('#config_router_add_ip_mask_iface_select_field').val(job.arg_1 || '');
                $('#config_router_add_ip_mask_ip_input_field').val(job.arg_2 || '');
                $('#config_router_add_ip_mask_mask_input_field').val(job.arg_3 || '0');
                break;
            case '101': // Включить NAT на интерфейсе
                UpdateRouterForm('config_router_add_nat_masquerade_script');
                FillDeviceSelectIntf("#config_router_add_nat_masquerade_iface_select_field", '#router_id', "Выберите линк", false);
                $('#config_router_add_nat_masquerade_iface_select_field').val(job.arg_1 || '');
                break;
            case '102': // Добавить маршрут
                UpdateRouterForm('config_router_add_route_script');
                $('#config_router_add_route_ip_input_field').val(job.arg_1 || '');
                $('#config_router_add_route_mask_input_field').val(job.arg_2 || '0');
                $('#config_router_add_route_gw_input_field').val(job.arg_3 || '');
                break;
            case '104': // Добавить сабинтерфейс с VLAN
                UpdateRouterForm('config_router_add_subinterface_script');
                FillDeviceSelectIntf("#config_router_add_subinterface_iface_select_field", '#router_id', "Выберите линк", false);
                $('#config_router_add_subinterface_iface_select_field').val(job.arg_1 || '');
                $('#config_router_add_subinterface_ip_input_field').val(job.arg_2 || '');
                $('#config_router_add_subinterface_mask_input_field').val(job.arg_3 || '0');
                $('#config_router_add_subinterface_vlan_input_field').val(job.arg_4 || '1');
                break;
            case '105': // Добавить IPIP-интерфейс
                UpdateRouterForm('config_router_add_ipip_tunnel_script');
                FillDeviceSelectIntf("#config_router_add_ipip_tunnel_iface_select_ip_field", '#router_id');
                $('#config_router_add_ipip_tunnel_iface_select_ip_field').val(job.arg_1 || '');
                $('#config_router_add_ipip_tunnel_end_ip_input_field').val(job.arg_2 || '');
                $('#config_router_add_ipip_tunnel_interface_ip_input_field').val(job.arg_3 || '');
                $('#config_router_add_ipip_tunnel_interface_name_field').val(job.arg_4 || '');
                break;
            case '106': // Добавить GRE-интерфейс
                UpdateRouterForm('config_router_add_gre_interface_script');
                FillDeviceSelectIntf("#config_router_add_gre_interface_select_ip_field", '#router_id');
                $('#config_router_add_gre_interface_select_ip_field').val(job.arg_1 || '');
                $('#config_router_add_gre_interface_end_ip_input_field').val(job.arg_2 || '');
                $('#config_router_add_gre_interface_ip_input_field').val(job.arg_3 || '');
                $('#config_router_add_gre_interface_name_field').val(job.arg_4 || '');
                break;
            case '107': // Включить ARP Proxy на интерфейсе
                UpdateRouterForm('config_router_add_arp_proxy_script');
                FillDeviceSelectIntf("#config_router_add_arp_proxy_iface_select_field", '#router_id', "Выберите линк", false);
                $('#config_router_add_arp_proxy_iface_select_field').val(job.arg_1 || '');
                break;
            case '109': // Добавить Port Forwarding для TCP
                UpdateRouterForm('config_router_add_port_forwarding_tcp_script');
                FillDeviceSelectIntf("#config_router_add_port_forwarding_tcp_iface_select_field", "#router_id", "Выберите линк", false);
                $('#config_router_add_port_forwarding_tcp_iface_select_field').val(job.arg_1 || '');
                $('#config_router_add_port_forwarding_tcp_port_input_field').val(job.arg_2 || '')
                $('#config_router_add_port_forwarding_tcp_dest_ip_input_field').val(job.arg_3 || '')
                $('#config_router_add_port_forwarding_tcp_dest_port_input_field').val(job.arg_4 || '')
                break;
            case '110': // Добавить Port Forwarding для UDP
                UpdateRouterForm('config_router_add_port_forwarding_udp_script');
                FillDeviceSelectIntf("#config_router_add_port_forwarding_udp_iface_select_field", "#router_id", "Выберите линк", false);
                $('#config_router_add_port_forwarding_udp_iface_select_field').val(job.arg_1 || '');
                $('#config_router_add_port_forwarding_udp_port_input_field').val(job.arg_2 || '')
                $('#config_router_add_port_forwarding_udp_dest_ip_input_field').val(job.arg_3 || '')
                $('#config_router_add_port_forwarding_udp_dest_port_input_field').val(job.arg_4 || '')
                break;
            default:
                console.error('Unknown job type for editing:', job.job_id);
        }

        setTimeout(() => {
            const formArea = $('div[name="config_router_select_input"]');
            if (formArea.length > 0) {
                formArea.addClass('editing-form-area');
            }
        }, 100);
        }, 200)
    }
};

// Edit job in server
const EditJobInServer = function(server_id, job_id, network_guid) {
    const job = jobs.find(j => j.id === job_id);

    if (!job) {
        console.error('Job not found:', job_id);
        return;
    }

    EnterEditMode('server', job_id, job.job_id);

    // Set the select field to the job type
    const selectField = document.getElementById('config_server_job_select_field');
    if (selectField) {
        selectField.value = job.job_id.toString();

        // Trigger change event to show the form
        const event = new Event('change');
        selectField.dispatchEvent(event);

        // Fill in the form fields with job data
        setTimeout(() => {
            switch(job.job_id.toString()) {
            case '1': // ping (1 пакет)
                UpdateServerForm('config_server_ping_c_1_script');
                $('#config_server_ping_c_1_ip').val(job.arg_1 || '');
                break;
            case '200': // Запустить UDP сервер
                UpdateServerForm('config_server_start_udp_server_script');
                $('#config_server_start_udp_server_ip_input_field').val(job.arg_1 || '');
                $('#config_server_start_udp_server_port_input_field').val(job.arg_2 || '0');
                break;
            case '201': // Запустить TCP сервер
                UpdateServerForm('config_server_start_tcp_server_script');
                $('#config_server_start_tcp_server_ip_input_field').val(job.arg_1 || '');
                $('#config_server_start_tcp_server_port_input_field').val(job.arg_2 || '0');
                break;
            case '202': // Блокировать TCP/UDP порт
                UpdateServerForm('config_server_block_tcp_udp_port_script');
                $('#config_server_block_tcp_udp_port_input_field').val(job.arg_1 || '0');
                break;
            case '203': // Запустить DHCP сервер
                UpdateServerForm('config_server_add_dhcp_server_script');
                FillDeviceSelectIntf('#config_server_add_dhcp_interface_select_iface_field', '#server_id', "Выберите линк", false);
                $('#config_server_add_dhcp_ip_range_1_input_field').val(job.arg_1 || '');
                $('#config_server_add_dhcp_ip_range_2_input_field').val(job.arg_2 || '');
                $('#config_server_add_dhcp_mask_input_field').val(job.arg_3 || '0');
                $('#config_server_add_dhcp_gateway_input_field').val(job.arg_4 || '');
                $('#config_server_add_dhcp_interface_select_iface_field').val(job.arg_5 || '');
                break;
            default:
                console.error('Unknown job type for editing:', job.job_id);
        }

        setTimeout(() => {
            const formArea = $('div[name="config_server_select_input"]');
            if (formArea.length > 0) {
                formArea.addClass('editing-form-area');
            }
        }, 100);
        }, 200)
    }
};
const EditJobInSwitch = function(switch_id, job_id, network_guid) {
    const job = jobs.find(j => j.id === job_id);

    if (!job) {
        console.error('Job not found:', job_id);
        return;
    }

    EnterEditMode('switch', job_id, job.job_id);

    // Set the select field to the job type
    const selectField = document.getElementById('config_switch_job_select_field');
    if (selectField) {
        selectField.value = job.job_id.toString();

        // Trigger change event to show the form
        const event = new Event('change');
        selectField.dispatchEvent(event);

        // Fill in the form fields with job data
        setTimeout(() => {
            switch(job.job_id.toString()) {
            case '6': 
                UpdateSwitchForm('config_switch_link_down_script');
                FillDeviceSelectIntf('#config_switch_link_down_iface_select_field','#switch_id' , "Выберете линк", false)
                $('#config_switch_link_down_iface_select_field').val(job.arg_1 || '');
                break;
            case '7': 
                UpdateSwitchForm('config_switch_sleep_script');
                $('#config_switch_sleep').val(job.arg_1 || '');
                break;
            
            default:
                console.error('Unknown job type for editing:', job.job_id);
        }

        setTimeout(() => {
            const formArea = $('div[name="config_switch_select_input"]');
            if (formArea.length > 0) {
                formArea.addClass('editing-form-area');
            }
        }, 100);
        }, 200)
    }
};