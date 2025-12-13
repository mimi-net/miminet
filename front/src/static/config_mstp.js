/**
 * MSTP (Multiple Spanning Tree Protocol) Configuration Module
 * 
 * This module provides UI for configuring MST instances and VLAN mappings
 * when MSTP mode (stp=3) is selected on a switch.
 */

const ConfigMSTP = function (currentDevice) {
    var modalId = 'MstpModal_' + currentDevice.data.id;
    var tableId = 'config_table_mstp_' + currentDevice.data.id;

    $('#' + modalId).remove();

    var buttonHTML = document.getElementById('config_button_mstp_script').innerHTML;
    var modalHTML = document.getElementById('config_modal_mstp_script').innerHTML;

    modalHTML = modalHTML.replace('id="MstpModal"', 'id="' + modalId + '"');

    var buttonElem = $(buttonHTML).appendTo('#config_switch_name');
    buttonElem.attr('data-bs-target', '#' + modalId);

    var modalElem = $(modalHTML).appendTo('body');

    $(document).ready(function () {
        $('[data-bs-toggle="tooltip"]').tooltip();
        setupMstpEventHandlers(currentDevice, modalId);
    });

    // Show/hide MSTP button based on STP mode
    updateMstpButtonVisibility(currentDevice);
};

function setupMstpEventHandlers(currentDevice, modalId) {
    var modal = $('#' + modalId);

    // Cancel button handlers
    modal.find('#mstpConfigurationCancelIcon, #mstpConfigurationCancel').on('click', function () {
        $('#' + modalId).modal('hide');
    });

    // Submit button handler
    modal.find('#mstpConfigurationSubmit').on('click', function () {
        saveMstpConfiguration(currentDevice, modalId);
        $('#' + modalId).modal('hide');
        updateMstpButtonStyle(currentDevice);

        // Reset network state
        SetNetworkPlayerState(-1);
        DrawGraph();
        PostNodesEdges();
    });

    // Add instance button
    modal.find('#addMstInstance').on('click', function () {
        addMstInstanceRow(modalId, currentDevice);
    });

    // Initialize with existing configuration
    initializeMstpForm(currentDevice, modalId);
}

function initializeMstpForm(currentDevice, modalId) {
    var modal = $('#' + modalId);
    var config = currentDevice.config;

    // Set region name
    modal.find('#mst_region_name').val(config.mst_region || '');

    // Set revision
    modal.find('#mst_revision').val(config.mst_revision || 0);

    // Clear existing instance rows
    modal.find('#mst_instances_container').empty();

    // Add existing MST instances
    if (config.mst_instances && config.mst_instances.length > 0) {
        config.mst_instances.forEach(function (instance) {
            addMstInstanceRow(modalId, currentDevice, instance);
        });
    } else {
        // Add default instance 0 (CIST)
        addMstInstanceRow(modalId, currentDevice, { instance_id: 0, vlans: [], priority: 32768 });
    }
}

function addMstInstanceRow(modalId, currentDevice, existingInstance) {
    var container = $('#' + modalId + ' #mst_instances_container');
    var instanceCount = container.find('.mst-instance-row').length;

    var instance = existingInstance || {
        instance_id: instanceCount,
        vlans: [],
        priority: 32768
    };

    var vlansStr = Array.isArray(instance.vlans) ? instance.vlans.join(', ') : '';

    var rowHtml = `
        <div class="mst-instance-row card mb-2 p-2">
            <div class="row g-2 align-items-center">
                <div class="col-2">
                    <label class="form-label small mb-0">Instance</label>
                    <input type="number" class="form-control form-control-sm mst-instance-id" 
                           value="${instance.instance_id}" min="0" max="64" readonly>
                </div>
                <div class="col-5">
                    <label class="form-label small mb-0">VLANs</label>
                    <input type="text" class="form-control form-control-sm mst-vlans" 
                           value="${vlansStr}" placeholder="1, 10, 20-30">
                </div>
                <div class="col-3">
                    <label class="form-label small mb-0">Priority</label>
                    <input type="number" class="form-control form-control-sm mst-priority" 
                           value="${instance.priority || 32768}" min="0" max="61440" step="4096">
                </div>
                <div class="col-2 d-flex align-items-end">
                    <button type="button" class="btn btn-outline-danger btn-sm remove-mst-instance" 
                            ${instance.instance_id === 0 ? 'disabled' : ''}>
                        <i class='bx bx-trash'></i>
                    </button>
                </div>
            </div>
        </div>
    `;

    container.append(rowHtml);

    // Add remove handler for new row
    container.find('.remove-mst-instance').last().on('click', function () {
        $(this).closest('.mst-instance-row').remove();
        renumberInstances(modalId);
    });
}

function renumberInstances(modalId) {
    $('#' + modalId + ' .mst-instance-row').each(function (index) {
        if (index > 0) { // Skip CIST (instance 0)
            $(this).find('.mst-instance-id').val(index);
        }
    });
}

function saveMstpConfiguration(currentDevice, modalId) {
    var modal = $('#' + modalId);

    // Save region configuration
    currentDevice.config.mst_region = modal.find('#mst_region_name').val() || null;
    currentDevice.config.mst_revision = parseInt(modal.find('#mst_revision').val()) || 0;

    // Save MST instances
    var instances = [];
    modal.find('.mst-instance-row').each(function () {
        var row = $(this);
        var instanceId = parseInt(row.find('.mst-instance-id').val());
        var vlansStr = row.find('.mst-vlans').val();
        var priority = parseInt(row.find('.mst-priority').val()) || 32768;

        var vlans = parseVlanList(vlansStr);

        instances.push({
            instance_id: instanceId,
            vlans: vlans,
            priority: priority
        });
    });

    currentDevice.config.mst_instances = instances.length > 0 ? instances : null;

    // Update node in global nodes array
    var index = nodes.findIndex(function (n) {
        return n.data.id === currentDevice.data.id;
    });

    if (index !== -1) {
        nodes[index].config = currentDevice.config;
    }
}

function parseVlanList(vlansStr) {
    if (!vlansStr || vlansStr.trim() === '') {
        return [];
    }

    var vlans = [];
    var parts = vlansStr.split(/[\s,]+/);

    parts.forEach(function (part) {
        part = part.trim();
        if (part === '') return;

        // Check for range (e.g., "10-20")
        if (part.includes('-')) {
            var range = part.split('-');
            var start = parseInt(range[0]);
            var end = parseInt(range[1]);

            if (!isNaN(start) && !isNaN(end) && start <= end) {
                for (var i = start; i <= end; i++) {
                    if (i >= 1 && i <= 4094 && !vlans.includes(i)) {
                        vlans.push(i);
                    }
                }
            }
        } else {
            var vlan = parseInt(part);
            if (!isNaN(vlan) && vlan >= 1 && vlan <= 4094 && !vlans.includes(vlan)) {
                vlans.push(vlan);
            }
        }
    });

    return vlans.sort(function (a, b) { return a - b; });
}

function updateMstpButtonVisibility(currentDevice) {
    var isMstpEnabled = currentDevice.config.stp === 3;
    var button = $('#config_button_mstp');

    if (isMstpEnabled) {
        button.show();
        updateMstpButtonStyle(currentDevice);
    } else {
        button.hide();
    }
}

function updateMstpButtonStyle(currentDevice) {
    var hasMstpConfig = currentDevice.config.mst_instances && 
                        currentDevice.config.mst_instances.length > 0;

    if (hasMstpConfig) {
        $('#config_button_mstp').addClass('btn-outline-primary').removeClass('btn-outline-secondary');
    } else {
        $('#config_button_mstp').removeClass('btn-outline-primary').addClass('btn-outline-secondary');
    }
}

// Function to be called when STP mode changes
function onStpModeChange(currentDevice, newMode) {
    currentDevice.config.stp = parseInt(newMode);
    updateMstpButtonVisibility(currentDevice);

    // Clear MSTP config if switching away from MSTP
    if (newMode !== 3) {
        currentDevice.config.mst_region = null;
        currentDevice.config.mst_revision = null;
        currentDevice.config.mst_instances = null;
    }
}
