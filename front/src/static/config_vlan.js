const ConfigVLAN = function (currentDevice) {
    var modalId = 'VlanModal_' + currentDevice.data.id;
    var tableId = 'config_table_vlan_' + currentDevice.data.id;

    $('#' + modalId).remove();

    var buttonHTML = document.getElementById('config_button_vlan_script').innerHTML;
    var modalHTML = document.getElementById('config_modal_vlan_script').innerHTML;
    var tableHTML = document.getElementById('config_table_vlan_script').innerHTML;

    modalHTML = modalHTML.replace('id="VlanModal"', 'id="' + modalId + '"');
    tableHTML = tableHTML.replace('id="config_table_vlan"', 'id="' + tableId + '"');

    var buttonElem = $(buttonHTML).appendTo('#config_switch_name');
    buttonElem.attr('data-bs-target', '#' + modalId);

    var modalElem = $(modalHTML).appendTo('body');
    var tableElem = $(tableHTML).appendTo('#' + modalId + ' .modal-body').hide();

    $(document).ready(function () {
        setupEventHandlers(currentDevice, modalId, tableId);
    });
};

function setupEventHandlers(currentDevice, modalId, tableId) {
    $('#' + modalId).find('#config_switch_vlan').off('click').on('click', function () {
        if ($(this).is(':checked')) {
            $('#' + tableId).show();
            generateTableContent(currentDevice, '#' + tableId);
        } else {
            $('#' + tableId).hide();
        }
    });

    $('#' + modalId).find('#vlanConfigrationCancelIcon, #vlanConfigrationCancel').on('click', function () {
        restoreFormData(currentDevice, '#' + tableId);
        $('#' + modalId).modal('hide');
    });

    $('#' + modalId).find('#vlanConfigrationSubmit').on('click', function () {
        if ($('#' + modalId).find('#config_switch_vlan').is(':checked')) {
            saveCurrentFormData(currentDevice, '#' + tableId);
        } else {
            resetInterfaceFields(currentDevice);
        }
        $('#' + modalId).modal('hide');
        updateVlanButtonStyle(currentDevice);

        // Reset network state
        SetNetworkPlayerState(-1);
        DrawGraph();
        PostNodesEdges();
    });

    $('#config_button_vlan').off('click').on('click', function () {
        if (areInterfaceFieldsFilled(currentDevice)) {
            $('#' + modalId).find('#config_switch_vlan').prop('checked', true);
            $('#' + tableId).show();
            generateTableContent(currentDevice, '#' + tableId);
        } else {
            $('#' + modalId).find('#config_switch_vlan').prop('checked', false);
            $('#' + tableId).hide();
        }
        $('#' + modalId).modal('show');
    });

    updateVlanButtonStyle(currentDevice);
}


function generateTableContent(currentDevice, tableSelector) {
    // Clearing previous lines in tbody
    $(tableSelector + ' tbody').empty();

    var edgesMap = new Map();
    for (var i = 0; i < edges.length; i++) {
        edgesMap.set(edges[i].data.id, edges[i]);
    }

    for (var i = 0; i < currentDevice.interface.length; i++) {
        var interface = currentDevice.interface[i];
        var connectedEdge = edgesMap.get(interface.connect);

        if (connectedEdge !== undefined) {
            var targetDeviceId = connectedEdge.data.target;

            // Checking whether the current device is the source or not
            if (connectedEdge.data.source === currentDevice.data.id) {
                targetDeviceId = connectedEdge.data.target;
            } else {
                targetDeviceId = connectedEdge.data.source;
            }

            var vlan = (interface.vlan !== null && interface.vlan !== undefined) ? interface.vlan : 1;
            var type_connection = (interface.type_connection !== null && interface.type_connection !== undefined) ? interface.type_connection : 0;

            var selectedAccess = type_connection === 0 ? 'selected' : '';
            var selectedTrunk = type_connection === 1 ? 'selected' : '';

            var row = '<tr data-id="' + interface.id + '">' +
                '<td>' + targetDeviceId + '</td>' +
                '<td><input type="text" value="' + vlan + '" class="form-control vlan-input" /></td>' +
                '<td>' +
                '<select class="form-select type-connection-select">' +
                '<option value="Access" ' + selectedAccess + '>Access</option>' +
                '<option value="Trunk" ' + selectedTrunk + '>Trunk</option>' +
                '</select>' +
                '</td>' +
                '</tr>';

            $(tableSelector + ' tbody').append(row);
        }
    }

    $('.type-connection-select').change(function () {
        var typeConnection = $(this).val();
        var vlanInput = $(this).closest('tr').find('.vlan-input');

        // Number from 1 to 4096
        var vlanPattern = '^(?:[1-9]|[1-9]\\d{1,2}|[1-3]\\d{3}|40[0-9]{2}|409[0-4])';

        // List of VLANs, separated by spaces or commas
        var vlanListPattern = '^' + vlanPattern + '(\\s*(,|\\s)\\s*' + vlanPattern + ')*$';

        if (typeConnection === 'Trunk') {
            vlanInput.attr('pattern', vlanListPattern);
        } else {
            vlanInput.attr('pattern', vlanPattern);
        }

    });
}

function saveCurrentFormData(currentDevice, tableSelector) {
    $(tableSelector + ' tbody tr').each(function (index, row) {
        var row = $(row);
        var interfaceId = row.data('id');
        var vlanInput = row.find('input').val();
        var type_connection = row.find('select').val() === 'Access' ? 0 : 1;

        var interface = currentDevice.interface.find(function (item) {
            return item.id === interfaceId;
        });

        if (interface) {
            var vlanSplit = /[\s,]+/;
            var vlanValues = type_connection === 1 ? vlanInput.split(vlanSplit).map(Number) : [Number(vlanInput)];
            var validVlanValues = vlanValues.every(function (value) {
                return value >= 1 && value <= 4094;
            });

            if (validVlanValues) {
                interface.vlan = type_connection === 1 ? vlanValues : vlanValues[0];
            }
            interface.type_connection = type_connection;
        };
    });
}

function restoreFormData(currentDevice, tableSelector) {
    $(tableSelector + ' tbody tr').each(function (index, row) {
        var row = $(row);
        var interfaceId = row.data('id');

        var interface = currentDevice.interface.find(function (item) {
            return item.id === interfaceId;
        });
        if (interface) {
            var vlanValue = interface.vlan;
            if (Array.isArray(vlanValue)) {
                vlanValue = vlanValue.join(', ');
            } else if (vlanValue === null || vlanValue === undefined) {
                vlanValue = 1;
            }

            row.find('input').val(vlanValue);
            row.find('select').val(interface.type_connection === 0 ? 'Access' : 'Trunk');
        }
    });
}

function updateVlanButtonStyle(currentDevice) {
    var isVlanEnabled = areInterfaceFieldsFilled(currentDevice);

    if (isVlanEnabled) {
        $('#config_button_vlan').addClass('btn-outline-primary').removeClass('btn-outline-secondary');
    } else {
        $('#config_button_vlan').removeClass('btn-outline-primary').addClass('btn-outline-secondary');
    }
}

function areInterfaceFieldsFilled(device) {
    return device.interface.some(interface =>
        interface.vlan !== null &&
        interface.vlan !== undefined &&
        interface.type_connection !== null &&
        interface.type_connection !== undefined
    );
}

function resetInterfaceFields(device) {
    device.interface.forEach(interface => {
        interface.vlan = null;
        interface.type_connection = null;
    });
}