const ActionWithInterface = function (n, i, fun) {

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

    let ip_addr = n.interface[i].ip || '';
    let netmask = n.interface[i].netmask || '';

    fun(iface_id, ip_addr, netmask, connected_to_host_label);

}

// Common setup for device configs with jobs, interfaces, and gateway.
// opts: { formFn, sharedFormFn, nameFn, jobFn, interfaceFn, gatewayFn, afterFn(n, shared) }
const showDeviceConfig = function(n, shared, opts) {
    if (editingJobId && editingDeviceType) {
        ExitEditMode(editingDeviceType);
    }

    let hostname = n.config.label || n.data.id;

    if (shared) {
        opts.sharedFormFn(n.data.id);
    } else {
        opts.formFn(n.data.id);
    }

    opts.nameFn(hostname);

    let deviceJobs = jobs ? jobs.filter(j => j.host_id === n.data.id) : [];
    opts.jobFn(deviceJobs, shared);

    $.each(n.interface, function(i) {
        ActionWithInterface(n, i, opts.interfaceFn);
    });

    if (n.interface.length && opts.gatewayFn) {
        opts.gatewayFn(n.config.default_gw || '');
    }

    if (opts.afterFn) opts.afterFn(n, shared);

    if (shared) {
        DisableFormInputs();
    }
}

const ShowHostConfig = function(n, shared = 0) {
    showDeviceConfig(n, shared, {
        formFn: ConfigHostForm,
        sharedFormFn: SharedConfigHostForm,
        nameFn: ConfigHostName,
        jobFn: ConfigHostJob,
        interfaceFn: ConfigHostInterface,
        gatewayFn: ConfigHostGateway,
    });
}

const ShowRouterConfig = function(n, shared = 0) {
    showDeviceConfig(n, shared, {
        formFn: ConfigRouterForm,
        sharedFormFn: SharedConfigRouterForm,
        nameFn: ConfigRouterName,
        jobFn: ConfigRouterJob,
        interfaceFn: ConfigRouterInterface,
        gatewayFn: ConfigRouterGateway,
        afterFn: function(n, shared) {
            ConfigVxlan(n);
            if (shared) DisableVXLANInputs(n);
        },
    });
}

const ShowServerConfig = function(n, shared = 0) {
    showDeviceConfig(n, shared, {
        formFn: ConfigServerForm,
        sharedFormFn: SharedConfigServerForm,
        nameFn: ConfigServerName,
        jobFn: ConfigServerJob,
        interfaceFn: ConfigServerInterface,
        gatewayFn: ConfigServerGateway,
    });
}

const ShowHubConfig = function(n, shared = 0){

    let hostname = n.config.label;
    hostname = hostname || n.data.id;

    // Create form
    if (shared){
        SharedConfigHubForm(n.data.id);
    } else {
        ConfigHubForm(n.data.id);
    }

    // Add hostname
    ConfigHubName(hostname);

    // Add interfaces
    $.each(n.interface, function (i) {
        ActionWithInterface(n, i, ConfigHubInterface)
    });

    if(n.interface.length){
        ConfigHubIndent();
    }

    if (shared){
        DisableFormInputs();
    }
}

const ShowSwitchConfig = function(n, shared = 0){

    let hostname = n.config.label;
    hostname = hostname || n.data.id;

    // Create form
    if (shared){
        SharedConfigSwitchForm(n.data.id);
    } else {
        ConfigSwitchForm(n.data.id);
    }

    // Add hostname
    ConfigSwitchName(hostname);
    let switch_jobs = [];

    if (jobs){
        switch_jobs = jobs.filter(j => j.host_id === n.data.id);
    }

    ConfigSwitchJob(switch_jobs, shared);

    //Add checkbox STP
//    ConfigSwtichSTP(n.config.stp);

    //Add checkbox RSTP
//    ConfigSwtichRSTP(n.config.rstp);
    ConfigRSTP(n);

    // Add VLAN
    ConfigVLAN(n);

    // Add interfaces
    $.each(n.interface, function (i) {
        ActionWithInterface(n, i, ConfigSwitchInterface)
    });

    if(n.interface.length){
        ConfigSwitchIndent();
    }

    if (shared){
        DisableFormInputs();
        DisableVLANInputs(n);
    }
}

const ShowEdgeConfig = function(edge_id, shared = 0){

    let ed = edges.find(ed => ed.data.id === edge_id);

    if (!ed){
        return;
    }

    let edge_source = ed.data.source;
    let edge_target = ed.data.target;
    let edge_loss = ed.data.loss_percentage || 0;
    let edge_duplicate = ed.data.duplicate_percentage || 0;

    // Create form
    if (shared){
        SharedConfigEdgeForm(edge_id);
    } else {
        ConfigEdgeForm(edge_id);
    }

    ConfigEdgeNetworkIssues(edge_loss, edge_duplicate);

    // Add source and target info
    ConfigEdgeEndpoints(edge_source, edge_target);

    if (shared){
        DisableFormInputs();
    }
}
