$('#config_host').load( "config_host.html" );

const config_content_id = "#config_content";
const config_main_form_id = "#config_main_form";

const ConfigHostForm = function(host_id){
    var form = document.getElementById('config_main_form_script').innerHTML;

    // Clear all child
    $(config_content_id).empty();

    // Add new form
    $(config_content_id).append(form);

    // Set host_id
    $('#host_id').val( host_id );
    $('#net_guid').val( network_guid );
}

const ConfigHostName = function(hostname){

    var text = document.getElementById('config_host_name_script').innerHTML;

    $(config_main_form_id).prepend((text));
    $('#config_host_name').val(hostname);
}

const ConfigHostInterface = function(name, ip, netmask){

    var elem = document.getElementById('config_host_interface_script');
    var eth = jQuery.extend({}, elem);

    if (!name){
        return;
    }

    eth.innerHTML = eth.innerHTML.replace(/config_host_iface_name_label_example/g, 'config_host_iface_name_label_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_host_iface_name_example/g, 'config_host_iface_name_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_host_ip_example/g, 'config_host_ip_' + name);
    eth.innerHTML = eth.innerHTML.replace(/config_host_mask_example/g, 'config_host_mask_' + name);

    var text = eth.innerHTML;

    $(text).insertBefore('#config_main_form_submit_button');
    $('#config_host_iface_name_' + name).val(name);
    $('#config_host_ip_' + name).val(ip);
    $('#config_host_mask_' + name).val(netmask);

}