const ConfigVLAN = function (currentDevice) {
    var buttonElem = document.getElementById('config_button_vlan_script');
    var modalElem = document.getElementById('config_modal_vlan_script');
    var table = document.getElementById('config_table_vlan_script');

    $(buttonElem.innerHTML).appendTo('#config_switch_name');
    $(modalElem.innerHTML).appendTo('body');

    $(document).ready(function () {
        $('#config_switch_vlan').off('click').on('click', function () {
            if ($(this).is(':checked')) {
                $('#switch_vlan').after(table.innerHTML);
                generateTableContent(currentDevice);
            } else {
                $('#config_table_vlan').remove();
            }
        });

        $('#vlanConfigrationCancelIcon').on('click', function () {
            restoreFormData(currentDevice);
            $('#VlanModal').modal('hide');
        });

        $('#vlanConfigrationCancel').on('click', function () {
            restoreFormData(currentDevice);
            $('#VlanModal').modal('hide');
        });

        $('#vlanConfigrationSubmit').on('click', function () {
            if ($('#config_switch_vlan').is(':checked')) {
                saveCurrentFormData(currentDevice);
            } else {
                resetInterfaceFields(currentDevice);
            }
            $('#VlanModal').modal('hide');

            // Reset network state
            SetNetworkPlayerState(-1);
            DrawGraph();
            PostNodesEdges()
        });

        $('#config_button_vlan').off('click').on('click', function () {
            if (areInterfaceFieldsFilled(currentDevice)) {
                $('#config_switch_vlan').prop('checked', true);
                if (!$('#config_table_vlan').is(':visible')) {
                    $('#switch_vlan').after(table.innerHTML);
                }
                generateTableContent(currentDevice);
            }
            else {
                $('#config_switch_vlan').prop('checked', false);
                $('#config_table_vlan').remove();
            }
        });
    });
}

function generateTableContent(currentDevice) {
    // Clearing previous lines in tbody
    $('#config_table_vlan tbody').empty();

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

            $('#config_table_vlan tbody').append(row);
        }
    }

    $('.type-connection-select').change(function () {
        var typeConnection = $(this).val();
        var vlanInput = $(this).closest('tr').find('.vlan-input');

        // Number from 1 to 4096
        var vlanPattern = '^(?:[1-9]|[1-9]\\d{1,2}|[1-3]\\d{3}|40[0-9]{2}|409[0-4])$';

        if (typeConnection === 'Trunk') {
            vlanInput.attr('pattern', vlanPattern + '(\\s*,\\s*' + vlanPattern + ')*$');
        } else {
            vlanInput.attr('pattern', vlanPattern);
        }

    });
}

function saveCurrentFormData(currentDevice) {
    $('#config_table_vlan tbody tr').each(function (index, row) {
        var row = $(row);
        var interfaceId = row.data('id');
        var vlanInput = row.find('input').val();
        var type_connection = row.find('select').val() === 'Access' ? 0 : 1;

        var interface = currentDevice.interface.find(function (item) {
            return item.id === interfaceId;
        });

        if (interface) {
            var vlanValues = type_connection === 1 ? vlanInput.split(',').map(Number) : [Number(vlanInput)];
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

function restoreFormData(currentDevice) {
    $('#config_table_vlan tbody tr').each(function (index, row) {
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