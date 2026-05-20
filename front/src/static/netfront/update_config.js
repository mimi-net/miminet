const UpdateHostConfiguration = function (data, host_id)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/host/save_config'),
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Exit edit mode on successful save
                if (editingJobId && editingDeviceType === 'host') {
                    ExitEditMode('host');
                }
                if (!data.warning){
                    // Update nodes
                    nodes = data.nodes;
                    // Update jobs
                    jobs = data.jobs;
                    
                    // Update graph
                    DrawGraph();
                }

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === host_id);

                if (!n) {
                    ClearConfigForm('Нет такого хоста');
                    return;
                }

                if (n.config.type === 'host'){
                    ShowHostConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не хост');
                    return;
                }

                if (data.warning){
                    HostWarningMsg(data.warning);
                }

                // Update job counter after successful configuration
                UpdateJobCounter('config_host_job_counter', host_id);
            }
        },
        error: function(xhr) {
            console.log('Не удалось обновить конфигурацию хоста');
            console.log(xhr);

            // Show error message to user
            let errorMsg = 'Ошибка при сохранении конфигурации';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMsg = xhr.responseJSON.message;
            }
            HostErrorMsg(errorMsg);

            // Exit edit mode on error to allow retry
            if (editingJobId && editingDeviceType === 'host') {
                ExitEditMode('host');
            }
        },
        dataType: 'json'
    });
}

// Delete job from host
const DeleteJobFromHost = function (host_id, job_id, network_guid)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    let data = {
      id: job_id,
      guid: network_guid,
    };

    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/host/delete_job'),
        data: data,
        encode: true,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update jobs
                jobs = data.jobs;

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === host_id);

                if (!n) {
                    ClearConfigForm('Нет такого хоста');
                    return;
                }

                if (n.config.type === 'host'){
                    ShowHostConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не хост');
                }

                // Update job counter after deletion
                UpdateJobCounter('config_host_job_counter', host_id);

            }
        },
        error: function(xhr) {
            console.log('Не удалось удалить команду');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Delete job from router
const DeleteJobFromRouter = function (router_id, job_id, network_guid)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    let data = {
      id: job_id,
      guid: network_guid,
    };

    $.ajax({
        type: 'POST',
        url: '/host/delete_job',
        data: data,
        encode: true,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update jobs
                jobs = data.jobs;

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === router_id);

                if (!n) {
                    ClearConfigForm('Нет такого хоста');
                    return;
                }

                if (n.config.type === 'router'){
                    ShowRouterConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не раутер');
                }

                // Update job counter after deletion
                UpdateJobCounter('config_router_job_counter', router_id);
            }
        },
        error: function(xhr) {
            console.log('Не удалось удалить команду');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

const DeleteJobFromSwitch = function (switch_id, job_id, network_guid)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    let data = {
      id: job_id,
      guid: network_guid,
    };

    $.ajax({
        type: 'POST',
        url: '/host/delete_job',
        data: data,
        encode: true,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update jobs
                jobs = data.jobs;

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === switch_id);

                if (!n) {
                    ClearConfigForm('Нет такого хоста');
                    return;
                }

                if (n.config.type === 'l2_switch'){
                    ShowSwitchConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не свитч');
                }
                UpdateJobCounter('config_switch_job_counter', switch_id);
            }
        },
        error: function(xhr) {
            console.log('Не удалось удалить команду');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Delete job from server
const DeleteJobFromServer = function (server_id, job_id, network_guid)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    let data = {
      id: job_id,
      guid: network_guid,
    };

    $.ajax({
        type: 'POST',
        url: '/host/delete_job',
        data: data,
        encode: true,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update jobs
                jobs = data.jobs;

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === server_id);

                if (!n) {
                    ClearConfigForm('Нет такого хоста');
                    return;
                }

                if (n.config.type === 'server'){
                    ShowServerConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не сервер');
                }

                // Update job counter after deletion
                UpdateJobCounter('config_server_job_counter', server_id);
            }
        },
        error: function(xhr) {
            console.log('Не удалось удалить команду');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Update router configuration
const UpdateRouterConfiguration = function (data, router_id)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/host/router_save_config'),
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {

                // Exit edit mode on successful save
                if (editingJobId && editingDeviceType === 'router') {
                    ExitEditMode('router');
                }

                // Update nodes
                if (data.nodes)
                {
                    nodes = data.nodes;
                }

                // Update jobs
                if (data.jobs)
                {
                    jobs = data.jobs;
                }

                // Update graph
                DrawGraph();

                // Ok, let's try to update router config form
                let n = nodes.find(n => n.data.id === router_id);

                if (!n) {
                    ClearConfigForm('Нет такого раутера');
                    return;
                }

                if (n.config.type === 'router'){
                    ShowRouterConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не раутер');
                    return;
                }

                if (data.warning)
                {
                    HostWarningMsg(data.warning);
                }

                // Update job counter after successful configuration
                UpdateJobCounter('config_router_job_counter', router_id);
            }

        },
        error: function(xhr) {
            console.log('Не удалось обновить конфигурацию хоста');
            console.log(xhr);

            // Show error message to user
            let errorMsg = 'Ошибка при сохранении конфигурации роутера';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMsg = xhr.responseJSON.message;
            }
            HostErrorMsg(errorMsg);

            // Exit edit mode on error to allow retry
            if (editingJobId && editingDeviceType === 'router') {
                ExitEditMode('router');
            }
        },
        dataType: 'json'
    });
}

// Update server configuration
const UpdateServerConfiguration = function (data, router_id)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/host/server_save_config'),
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {

                // Exit edit mode on successful save
                if (editingJobId && editingDeviceType === 'server') {
                    ExitEditMode('server');
                }

                if (!data.warning){

                    if (data.nodes){
                        nodes = data.nodes;
                    }

                    if (data.jobs){
                        jobs = data.jobs;
                    }

                    // Update graph
                    DrawGraph();
                }

                // Ok, let's try to update router config form
                let n = nodes.find(n => n.data.id === router_id);

                if (!n) {
                    ClearConfigForm('Нет такого сервера');
                    return;
                }

                if (n.config.type === 'server'){
                    ShowServerConfig(n);
                } else {
                    ClearConfigForm('Узел есть, но это не сервер');
                    return;
                }

                if (data.warning)
                {
                    ServerWarningMsg(data.warning);
                }

                // Update job counter after successful configuration
                UpdateJobCounter('config_server_job_counter', router_id);
            }

        },
        error: function(xhr) {
            console.log('Не удалось обновить конфигурацию сервера');
            console.log(xhr);

            // Show error message to user
            let errorMsg = 'Ошибка при сохранении конфигурации сервера';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMsg = xhr.responseJSON.message;
            }
            HostErrorMsg(errorMsg);

            // Exit edit mode on error to allow retry
            if (editingJobId && editingDeviceType === 'server') {
                ExitEditMode('server');
            }
        },
        dataType: 'json'
    });
}

// Update hub configuration
const UpdateHubConfiguration = function (data, hub_id)
{
    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/host/hub_save_config'),
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                // Update nodes
                nodes = data.nodes;

                // We don't clear packets and RunButtonState.
                // Hub can change only names

                // Update graph
                DrawGraph();

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === hub_id);

                if (!n) {
                    ClearConfigForm('Нет такого узла');
                    return;
                }

                if (n.config.type === 'l1_hub'){
                    ShowHubConfig(n);
                } else {
                    ClearConfigForm('Нет такого хаба');
                }
            }
        },
        error: function(xhr) {
            console.log('Cannot update host config');
            console.log(xhr);
        },
        dataType: 'json'
    });
}

// Update Switch configuration
const UpdateSwitchConfiguration = function (data, switch_id)
{
    // Reset network player
    SetNetworkPlayerState(-1);

    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/host/switch_save_config'),
        data: data,
        success: function(data, textStatus, xhr) {

            if (xhr.status === 200)
            {
                if (editingJobId && editingDeviceType === 'switch') {
                    ExitEditMode('switch');
                }
                if (!data.warning){

                    // Update nodes
                    nodes = data.nodes;

                    // Update jobs
                    jobs = data.jobs;

                    // Update graph
                    DrawGraph();
                }

                // We don't clear packets and RunButtonState.
                // Hub can change only names

                // Ok, let's try to update host config form
                let n = nodes.find(n => n.data.id === switch_id);

                if (!n) {
                    ClearConfigForm('Нет такого узла');
                    return;
                }

                if (n.config.type === 'l2_switch'){
                    ShowSwitchConfig(n);
                } else {
                    ClearConfigForm('Нет такого свитча');
                }
                if (data.warning){
                    SwitchWarningMsg(data.warning)
                }
                UpdateJobCounter('config_switch_job_counter', switch_id);
            }
        },
        error: function(xhr) {
            console.log('Cannot update switch config');
            console.log(xhr);
            // Show error message to user
            let errorMsg = 'Ошибка при сохранении конфигурации свитча';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMsg = xhr.responseJSON.message;
            }
            HostErrorMsg(errorMsg);

            // Exit edit mode on error to allow retry
            if (editingJobId && editingDeviceType === 'switch') {
                ExitEditMode('switch');
            }
        },
        dataType: 'json'
    });
}

