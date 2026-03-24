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

// Update host configuration
const UpdateHostConfiguration = function (data, host_id)
{
    SetNetworkPlayerState(-1);

    $.ajax({
        type: 'POST',
        url: '/host/save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                if (editingJobId && editingDeviceType === 'host') {
                    ExitEditMode('host');
                }
                if (!data.warning){
                    nodes = data.nodes;
                    jobs = data.jobs;
                    DrawGraph();
                }

                let n = nodes.find(n => n.data.id === host_id);
                if (!n) { ClearConfigForm('Нет такого хоста'); return; }

                if (n.config.type === 'host'){
                    ShowHostConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не хост');
                    return;
                }

                if (data.warning) HostWarningMsg(data.warning);
                UpdateJobCounter('config_host_job_counter', host_id);
            }
        },
        error: function(xhr) {
            handleConfigError(xhr, 'host', 'Ошибка при сохранении конфигурации');
        },
        dataType: 'json'
    });
}

// Update router configuration
const UpdateRouterConfiguration = function (data, router_id)
{
    SetNetworkPlayerState(-1);

    $.ajax({
        type: 'POST',
        url: '/host/router_save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                if (editingJobId && editingDeviceType === 'router') {
                    ExitEditMode('router');
                }

                if (data.nodes) nodes = data.nodes;
                if (data.jobs) jobs = data.jobs;
                DrawGraph();

                let n = nodes.find(n => n.data.id === router_id);
                if (!n) { ClearConfigForm('Нет такого раутера'); return; }

                if (n.config.type === 'router'){
                    ShowRouterConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не раутер');
                    return;
                }

                if (data.warning) HostWarningMsg(data.warning);
                UpdateJobCounter('config_router_job_counter', router_id);
            }
        },
        error: function(xhr) {
            handleConfigError(xhr, 'router', 'Ошибка при сохранении конфигурации роутера');
        },
        dataType: 'json'
    });
}

// Update server configuration
const UpdateServerConfiguration = function (data, router_id)
{
    SetNetworkPlayerState(-1);

    $.ajax({
        type: 'POST',
        url: '/host/server_save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                if (editingJobId && editingDeviceType === 'server') {
                    ExitEditMode('server');
                }

                if (!data.warning){
                    if (data.nodes) nodes = data.nodes;
                    if (data.jobs) jobs = data.jobs;
                    DrawGraph();
                }

                let n = nodes.find(n => n.data.id === router_id);
                if (!n) { ClearConfigForm('Нет такого сервера'); return; }

                if (n.config.type === 'server'){
                    ShowServerConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не сервер');
                    return;
                }

                if (data.warning) ServerWarningMsg(data.warning);
                UpdateJobCounter('config_server_job_counter', router_id);
            }
        },
        error: function(xhr) {
            handleConfigError(xhr, 'server', 'Ошибка при сохранении конфигурации сервера');
        },
        dataType: 'json'
    });
}

// Update hub configuration
const UpdateHubConfiguration = function (data, hub_id)
{
    $.ajax({
        type: 'POST',
        url: '/host/hub_save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                nodes = data.nodes;
                DrawGraph();

                let n = nodes.find(n => n.data.id === hub_id);
                if (!n) { ClearConfigForm('Нет такого узла'); return; }

                if (n.config.type === 'l1_hub'){
                    ShowHubConfig(n);
                } else {
                    ClearConfigForm('Нет такого хаба');
                }
            }
        },
        error: function(xhr) {
            console.log('Cannot update hub config');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Update Switch configuration
const UpdateSwitchConfiguration = function (data, switch_id)
{
    SetNetworkPlayerState(-1);

    $.ajax({
        type: 'POST',
        url: '/host/switch_save_config',
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                if (editingJobId && editingDeviceType === 'switch') {
                    ExitEditMode('switch');
                }
                if (!data.warning){
                    nodes = data.nodes;
                    jobs = data.jobs;
                    DrawGraph();
                }

                let n = nodes.find(n => n.data.id === switch_id);
                if (!n) { ClearConfigForm('Нет такого узла'); return; }

                if (n.config.type === 'l2_switch'){
                    ShowSwitchConfig(n);
                } else {
                    ClearConfigForm('Нет такого свитча');
                }
                if (data.warning) SwitchWarningMsg(data.warning);
                UpdateJobCounter('config_switch_job_counter', switch_id);
            }
        },
        error: function(xhr) {
            handleConfigError(xhr, 'switch', 'Ошибка при сохранении конфигурации свитча');
        },
        dataType: 'json'
    });
}
