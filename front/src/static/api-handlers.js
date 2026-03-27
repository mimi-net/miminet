const UpdateEdgeConfiguration = (data) => {
    SetNetworkPlayerState(-1);

    return $.ajax({
        type: 'POST',
        url: '/edge/save_config',
        data: data,
        complete: function() {
            DrawGraph();
            $('#config_edge_main_form_submit_button').html('Сохранить');
        },
        error: function(xhr) {
            console.log('Не удалось обновить конфигурацию ребра');
            console.log(xhr);
        },
        dataType: 'json'
    });
};

// Generic delete job handler for all device types
const DeleteJobFromDevice = function(device_id, job_id, network_guid, expectedType, showConfigFn, counterSelector) {
    SetNetworkPlayerState(-1);

    $.ajax({
        type: 'POST',
        url: '/host/delete_job',
        data: { id: job_id, guid: network_guid },
        encode: true,
        success: function(data, textStatus, xhr) {
            if (xhr.status === 200) {
                jobs = data.jobs;
                DrawGraph();

                let n = nodes.find(n => n.data.id === device_id);
                if (!n) {
                    ClearConfigForm('Нет такого устройства');
                    return;
                }

                if (n.config.type === expectedType) {
                    showConfigFn(n);
                } else {
                    ClearConfigForm('Тип устройства не совпадает');
                }

                UpdateJobCounter(counterSelector, device_id);
            }
        },
        error: function(xhr) {
            console.log('Не удалось удалить команду');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

const DeleteJobFromHost = function(host_id, job_id, network_guid) {
    DeleteJobFromDevice(host_id, job_id, network_guid, 'host', ShowHostConfig, 'config_host_job_counter');
}

const DeleteJobFromRouter = function(router_id, job_id, network_guid) {
    DeleteJobFromDevice(router_id, job_id, network_guid, 'router', ShowRouterConfig, 'config_router_job_counter');
}

const DeleteJobFromSwitch = function(switch_id, job_id, network_guid) {
    DeleteJobFromDevice(switch_id, job_id, network_guid, 'l2_switch', ShowSwitchConfig, 'config_switch_job_counter');
}

const DeleteJobFromServer = function(server_id, job_id, network_guid) {
    DeleteJobFromDevice(server_id, job_id, network_guid, 'server', ShowServerConfig, 'config_server_job_counter');
}

// Generic error handler for device configuration updates
const handleConfigError = function(xhr, deviceType, errorPrefix) {
    console.log(errorPrefix);
    console.log(xhr);

    let errorMsg = errorPrefix;
    if (xhr.responseJSON && xhr.responseJSON.message) {
        errorMsg = xhr.responseJSON.message;
    }
    HostErrorMsg(errorMsg);

    if (editingJobId && editingDeviceType === deviceType) {
        ExitEditMode(deviceType);
    }
}

// Generic device configuration update handler
// opts: { url, deviceId, deviceType, expectedType, showConfigFn, warningFn, counterSelector, errorPrefix, resetPlayer, skipDrawOnWarning }
const UpdateDeviceConfiguration = function(data, opts) {
    if (opts.resetPlayer !== false) {
        SetNetworkPlayerState(-1);
    }

    $.ajax({
        type: 'POST',
        url: opts.url,
        data: data,
        success: function(data, textStatus, xhr) {
            if (xhr.status === 200) {
                if (editingJobId && editingDeviceType === opts.deviceType) {
                    ExitEditMode(opts.deviceType);
                }

                const shouldDraw = opts.skipDrawOnWarning ? !data.warning : true;
                if (shouldDraw) {
                    if (data.nodes) nodes = data.nodes;
                    if (data.jobs) jobs = data.jobs;
                    DrawGraph();
                }

                let n = nodes.find(n => n.data.id === opts.deviceId);
                if (!n) { ClearConfigForm('Нет такого устройства'); return; }

                if (n.config.type === opts.expectedType) {
                    opts.showConfigFn(n);
                } else {
                    ClearConfigForm('Тип устройства не совпадает');
                    return;
                }

                if (data.warning && opts.warningFn) opts.warningFn(data.warning);
                if (opts.counterSelector) {
                    UpdateJobCounter(opts.counterSelector, opts.deviceId);
                }
            }
        },
        error: function(xhr) {
            if (opts.errorPrefix) {
                handleConfigError(xhr, opts.deviceType, opts.errorPrefix);
            } else {
                console.log('Cannot update ' + opts.deviceType + ' config');
                console.log(xhr);
            }
        },
        dataType: 'json'
    });
}

const UpdateHostConfiguration = function(data, host_id) {
    UpdateDeviceConfiguration(data, {
        url: '/host/save_config',
        deviceId: host_id,
        deviceType: 'host',
        expectedType: 'host',
        showConfigFn: ShowHostConfig,
        warningFn: HostWarningMsg,
        counterSelector: 'config_host_job_counter',
        errorPrefix: 'Ошибка при сохранении конфигурации',
        skipDrawOnWarning: true,
    });
}

const UpdateRouterConfiguration = function(data, router_id) {
    UpdateDeviceConfiguration(data, {
        url: '/host/router_save_config',
        deviceId: router_id,
        deviceType: 'router',
        expectedType: 'router',
        showConfigFn: ShowRouterConfig,
        warningFn: HostWarningMsg,
        counterSelector: 'config_router_job_counter',
        errorPrefix: 'Ошибка при сохранении конфигурации роутера',
    });
}

const UpdateServerConfiguration = function(data, server_id) {
    UpdateDeviceConfiguration(data, {
        url: '/host/server_save_config',
        deviceId: server_id,
        deviceType: 'server',
        expectedType: 'server',
        showConfigFn: ShowServerConfig,
        warningFn: ServerWarningMsg,
        counterSelector: 'config_server_job_counter',
        errorPrefix: 'Ошибка при сохранении конфигурации сервера',
        skipDrawOnWarning: true,
    });
}

const UpdateHubConfiguration = function(data, hub_id) {
    UpdateDeviceConfiguration(data, {
        url: '/host/hub_save_config',
        deviceId: hub_id,
        deviceType: 'l1_hub',
        expectedType: 'l1_hub',
        showConfigFn: ShowHubConfig,
        resetPlayer: false,
    });
}

const UpdateSwitchConfiguration = function(data, switch_id) {
    UpdateDeviceConfiguration(data, {
        url: '/host/switch_save_config',
        deviceId: switch_id,
        deviceType: 'switch',
        expectedType: 'l2_switch',
        showConfigFn: ShowSwitchConfig,
        warningFn: SwitchWarningMsg,
        counterSelector: 'config_switch_job_counter',
        errorPrefix: 'Ошибка при сохранении конфигурации свитча',
        skipDrawOnWarning: true,
    });
}
