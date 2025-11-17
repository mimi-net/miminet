const ConfigVxlan = function (currentDevice) {
    var modalId = 'VxlanConfigModal' + currentDevice.data.id;
    var tableId = 'VxlanConfigTable' + currentDevice.data.id;

    $('#' + modalId).remove();

    var buttonElem = document.getElementById('config_button_vxlan_script');
    var modalElem = document.getElementById('config_modal_vxlan_script');
    var tableElem = document.getElementById('config_table_vxlan_script');
    
    if (!buttonElem || !modalElem || !tableElem) {
        return;
    }
    
    var buttonHTML = buttonElem.innerHTML;
    var modalHTML = modalElem.innerHTML;
    var tableHTML = tableElem.innerHTML;    

    modalHTML = modalHTML.replace('id="VxlanModal"', 'id="' + modalId + '"');
    tableHTML = tableHTML.replace('id="config_table_vxlan"', 'id="' + tableId + '"');

    var buttonElem = $(buttonHTML).insertAfter('#config_router_name');

    buttonElem.attr('data-bs-target', '#' + modalId);

    var modalElem = $(modalHTML).appendTo('body');
    var tableElem = $(tableHTML).appendTo('#' + modalId + ' .modal-body').hide();

    $(document).ready(function () {
        $('[data-bs-toggle="tooltip"]').tooltip();
        setupVxlanEventHandlers(currentDevice, modalId, tableId);
    });
}

function setupVxlanEventHandlers(currentDevice, modalId, tableId) {
    $('#' + modalId).find('#config_vxlan_switch').off('click').on('click', function () {
        if ($(this).is(':checked')) {
            $('#' + tableId).show();
            let ifaceToDeviseList = getInterfaceAndConnectedNodes(currentDevice);
            generateDropdownMenues(tableId, ifaceToDeviseList);
            generateNetworkInterfacesContent(tableId, ifaceToDeviseList);
            generateClientsContent(tableId, ifaceToDeviseList);
        } else {
            resetVxlanInterfaceFields(currentDevice);
            restoreVxlanFormData(tableId);
            $('#' + tableId).hide();
        }
    });

    $('#' + modalId).find('#vxlanConfigurationCancelIcon').on('click', function () {
        $('#' + modalId).modal('hide');
    });

    $('#' + modalId).on('hidden.bs.modal.myNamespace', function () {
        updateVxlanButtonStyle(currentDevice);

        SetNetworkPlayerState(-1);
        DrawGraph();
        PostNodesEdges();
    });

    $('#' + modalId).find('#vxlanConfigrationSubmit').on('click', function () {
        $('#' + modalId).modal('hide');
    });

    $('#config_button_vxlan').off('click').on('click', function () {
        if (areVxlanInterfaceFieldsFilled(currentDevice)) {
            $('#' + modalId).find('#config_vxlan_switch').prop('checked', true);
            $('#' + tableId).show();
            let ifaceToDeviseList = getInterfaceAndConnectedNodes(currentDevice);
            generateDropdownMenues(tableId, ifaceToDeviseList);
            generateNetworkInterfacesContent(tableId, ifaceToDeviseList);
            generateClientsContent(tableId, ifaceToDeviseList);
        } else {
            $('#' + modalId).find('#config_vxlan_switch').prop('checked', false);
            $('#' + tableId).hide();
        }
        $('#' + modalId).modal('show');
    });
    $('#' + tableId).find('.add-client-vxlan-interface').off('click').on('click', function () {
        addClientVxlanInterface(currentDevice, tableId, modalId);
        let ifaceToDeviseList = getInterfaceAndConnectedNodes(currentDevice);
        generateClientsContent(tableId, ifaceToDeviseList);
    });

    $('#' + tableId).find('.add-network-vxlan-interface').off('click').on('click', function () {
        addNetworkVxlanInterface(currentDevice, tableId, modalId);
        let ifaceToDeviseList = getInterfaceAndConnectedNodes(currentDevice);
        generateNetworkInterfacesContent(tableId, ifaceToDeviseList);
    });

    updateVxlanButtonStyle(currentDevice);
}

function getInterfaceAndConnectedNodes(currentDevice) {
    const result = [];

    const edgesMap = new Map();
    for (var i = 0; i < edges.length; i++) {
        edgesMap.set(edges[i].data.id, edges[i]);
    }

    const nodesMap = new Map();
    for (var i = 0; i < nodes.length; i++) {
        nodesMap.set(nodes[i].data.id, nodes[i].data.label);
    }

    for (let i = 0; i < currentDevice.interface.length; i++) {
        let interfaceInfo = currentDevice.interface[i];
        let connectedEdge = edgesMap.get(interfaceInfo.connect);
        if (connectedEdge !== undefined) {
            let targetDeviceId;
            if (connectedEdge.data.source === currentDevice.data.id) {
                targetDeviceId = connectedEdge.data.target;
            } else {
                targetDeviceId = connectedEdge.data.source;
            }
            let connectedNode = nodesMap.get(targetDeviceId);
            result.push([interfaceInfo, connectedNode]);
        }
    }

    return result;
}

function generateClientsContent(tableId, ifaceToDeviseList) {
    const devices_list = $('#' + tableId).find('.devices-list')[0];
    while (devices_list.firstChild) {
        devices_list.removeChild(devices_list.firstChild);
    }
    ifaceToDeviseList.forEach(([iface, connectedNode]) => {
        if (iface.vxlan_vni !== null && iface.vxlan_vni !== undefined && iface.vxlan_connection_type === 0) {
            const row = createClientRow(iface, connectedNode, tableId)
            devices_list.appendChild(row)
        }
    });
}

function generateNetworkInterfacesContent(tableId, ifaceToDeviseList) {
    const interfaces_list = $('#' + tableId).find('.interfaces-list')[0];

    while (interfaces_list.firstChild) {
        interfaces_list.removeChild(interfaces_list.firstChild);
    }

    ifaceToDeviseList.forEach(([iface, connectedNode]) => {
        var connectionType = iface.vxlan_connection_type;
        let targetIpList = iface.vxlan_vni_to_target_ip;
        if (connectionType === 1 && targetIpList !== null && targetIpList !== undefined && targetIpList) {
            for (let j = 0; j < targetIpList.length; j++) {
                const row = createNetIfaceRow(iface, connectedNode, targetIpList[j][0], targetIpList[j][1], tableId);
                interfaces_list.appendChild(row)
            }
        }
    });
}

function generateDropdownMenues(tableId, ifaceToDeviseList) {
    const select_client_link = $('#' + tableId).find('.client-device')[0];
    const select_out_link = $('#' + tableId).find('.out-interface')[0];
    while (select_client_link.firstChild) {
        select_client_link.removeChild(select_client_link.firstChild);
    }
    while (select_out_link.firstChild) {
        select_out_link.removeChild(select_out_link.firstChild);
    }
    ifaceToDeviseList.forEach(([iface, connectedNode]) => {

        const option = document.createElement('option');
        option.value = iface.id;
        option.textContent = connectedNode;
        select_client_link.appendChild(option);

        const option2 = document.createElement('option');
        option2.value = iface.id;
        option2.textContent = connectedNode;
        select_out_link.appendChild(option2);
    }
    );

}


function createNetIfaceRow(iface, deviceName, vni, ip, tableId) {
    const networkRow = document.createElement('li');
    networkRow.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center', 'network-interface');
    networkRow.dataset.id = iface.id;
    networkRow.textContent = `Линк к: ${deviceName}, VNI: ${vni}, Удаленный IP: ${ip}`;
    const removeButton = document.createElement('button');
    removeButton.classList.add('btn', 'btn-danger', 'btn-sm');
    removeButton.textContent = 'Удалить';
    removeButton.onclick = function () {
        removeInterface(iface, vni, ip, tableId);
    };
    networkRow.appendChild(removeButton);
    return networkRow;
}

function createClientRow(iface, deviceName, tableId) {
    const clientRow = document.createElement('li');
    clientRow.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center', 'client-interface');
    clientRow.dataset.id = iface.id;
    clientRow.textContent = `Линк к: ${deviceName}, VNI: ${iface.vxlan_vni}`;
    const removeButton = document.createElement('button');
    removeButton.classList.add('btn', 'btn-danger', 'btn-sm');
    removeButton.textContent = 'Удалить';
    removeButton.onclick = function () {
        removeDevice(iface, tableId);
    };
    clientRow.appendChild(removeButton);
    return clientRow;
}

function restoreVxlanFormData(tableId) {
    clearClientFields(tableId);
    clearNetworkFields(tableId);
}

function isValidVNI(vni) {
    const num = Number(vni);
    return Number.isInteger(num) && num >= 1 && num <= 16777214;
}

function isValidIP(ip) {
    const ipv4Regex = /^(25[0-5]|2[0-4]\d|[0-1]?\d{1,2})(\.(25[0-5]|2[0-4]\d|[0-1]?\d{1,2})){3}$/;
    return ipv4Regex.test(ip);
}

function isDuplicateNetworkEntry(currentDevice, vni, targetIp) {
    return currentDevice.interface.some(iface =>
        iface.vxlan_connection_type === 1 &&
        iface.vxlan_vni_to_target_ip &&
        iface.vxlan_vni_to_target_ip.some(entry => entry[0] === vni && entry[1] === targetIp)
    );
}

function isLinkAlreadyAdded(currentDevice, interfaceId, role) {
    return currentDevice.interface.some(iface => {
        if (iface.id === interfaceId) {
            if (role === 'client') {
                return iface.vxlan_connection_type === 1 && Array.isArray(iface.vxlan_vni_to_target_ip) && iface.vxlan_vni_to_target_ip.length > 0;
            } else if (role === 'network') {
                return iface.vxlan_connection_type === 0 && iface.vxlan_vni !== null;
            }
        }
        return false;
    });
}


function addClientVxlanInterface(currentDevice, tableId, modalId) {
    const vni = $('#' + tableId).find('.client-vni').val();
    let deviceEntry = $('#' + tableId).find('.client-device').find('option:selected').val();

    if (!deviceEntry) {
        showAlert("Пожалуйста, выберите клиентский интерфейс.", "warning", modalId);
        return;
    }

    if (!isValidVNI(vni)) {
        showAlert("Неверный VNI. Пожалуйста, введите число от 1 до 16777214.", "danger", modalId);
        return;
    }

    if (isLinkAlreadyAdded(currentDevice, deviceEntry, 'client')) {
        showAlert("Этот интерфейс уже используется как сетевой. Пожалуйста, выберите другой интерфейс.", "danger", modalId);
        return;
    }

    if (deviceEntry === null || deviceEntry === undefined || deviceEntry === '') {
        return;
    }
    var iface = currentDevice.interface.find(function (item) {
        return item.id === deviceEntry;
    });
    if (iface) {
          if (iface.vxlan_connection_type === 0 && iface.vxlan_vni !== null && iface.vxlan_vni !== undefined) {
            showAlert("Этот интерфейс уже привязан к VNI: " + String(iface.vxlan_vni), "warning", modalId);
            return;
        }
        iface.vxlan_vni = Number(vni);
        iface.vxlan_connection_type = 0;
        iface.vxlan_vni_to_target_ip = null;
    }
    clearClientFields(tableId);
}

function addNetworkVxlanInterface(currentDevice, tableId, modalId) {
    const vni = $('#' + tableId).find('.network-vni').val();
    const targetIp = $('#' + tableId).find('.remote-vtep-ip').val();
    let deviceEntry = $('#' + tableId).find('.out-interface').find('option:selected').val();

    if (!deviceEntry) {
        showAlert("Пожалуйста, выберите исходящий интерфейс.", "warning", modalId);
        return;
    }

    if (!isValidVNI(vni)) {
        showAlert("Неверный VNI. Пожалуйста, введите число от 1 до 16777214.", "danger", modalId);
        return;
    }

    if (!isValidIP(targetIp)) {
        showAlert("Неверный IP-адрес. Пожалуйста, введите действительный IPv4 адрес.", "danger", modalId);
        return;
    }

    if (isLinkAlreadyAdded(currentDevice, deviceEntry, 'network')) {
        showAlert("Этот интерфейс уже используется как клиентский. Пожалуйста, выберите другой интерфейс.", "danger", modalId);
        return;
    }

    if (isDuplicateNetworkEntry(currentDevice, vni, targetIp)) {
        showAlert("Такая запись VXLAN уже существует на этом интерфейсе.", "warning", modalId);
        return;
    }

    if (deviceEntry === null || deviceEntry === undefined || deviceEntry === '') {
        return;
    }
    var iface = currentDevice.interface.find(function (item) {
        return item.id === deviceEntry;
    });
    if (iface) {
        iface.vxlan_vni = null;
        iface.vxlan_connection_type = 1;
        if (!Array.isArray(iface.vxlan_vni_to_target_ip)) {
            iface.vxlan_vni_to_target_ip = [];
        }

        iface.vxlan_vni_to_target_ip.push([vni, targetIp]);
    }
    clearNetworkFields(tableId);
}

function clearClientFields(tableId) {
    $('#' + tableId).find('.client-vni').val('');
    $('#' + tableId).find('.client-device').prop('selectedIndex', 0);
}

function clearNetworkFields(tableId) {
    $('#' + tableId).find('.network-vni').val('');
    $('#' + tableId).find('.remote-vtep-ip').val('');
    $('#' + tableId).find('.out-interface').prop('selectedIndex', 0);
}

function resetVxlanInterfaceFields(currentDevice) {
    currentDevice.interface.forEach(iface => {
        iface.vxlan_vni = null;
        iface.vxlan_connection_type = null;
        iface.vxlan_vni_to_target_ip = null;
    });
}

function areVxlanInterfaceFieldsFilled(currentDevice) {
    return currentDevice.interface.some(iface => ((iface.vxlan_vni !== null && iface.vxlan_vni !== undefined) || (iface.vxlan_vni_to_target_ip !== null && iface.vxlan_vni_to_target_ip !== undefined && iface.vxlan_vni_to_target_ip.length > 0)) && (iface.vxlan_connection_type !== null && iface.vxlan_connection_type !== undefined));
}

function updateVxlanButtonStyle(currentDevice) {
    var isVxlanEnabled = areVxlanInterfaceFieldsFilled(currentDevice);

    if (isVxlanEnabled) {
        $('#config_button_vxlan').addClass('btn-outline-primary').removeClass('btn-outline-secondary');
    } else {
        $('#config_button_vxlan').removeClass('btn-outline-primary').addClass('btn-outline-secondary');
    }
}

function removeDevice(iface, tableId) {
    iface.vxlan_vni = null;
    iface.vxlan_connection_type = null;
    iface.vxlan_vni_to_target_ip = null;

    const deviceList = $('#' + tableId).find('.devices-list')[0];
    const deviceItems = deviceList.getElementsByClassName('client-interface');

    for (let item of deviceItems) {
        if (item.dataset.id === iface.id) {
            deviceList.removeChild(item);
            break;
        }
    }
}

function removeInterface(iface, vni, targetIp, tableId) {
    const interfaceList = $('#' + tableId).find('.interfaces-list')[0];
    const interfaceItems = interfaceList.getElementsByClassName('network-interface');
    if (Array.isArray(iface.vxlan_vni_to_target_ip)) {
        iface.vxlan_vni_to_target_ip = iface.vxlan_vni_to_target_ip.filter(item => item[0] !== vni || item[1] !== targetIp);
    }

    for (let item of interfaceItems) {
        const textContent = item.textContent || item.innerText;
        if (textContent.includes(`VNI: ${vni}`) && textContent.includes(`Удаленный IP: ${targetIp}`)) {
            interfaceList.removeChild(item);
            break;
        }
    }
}

function showAlert(message, type = 'info', modalId) {
    const alertContainer = $('#' + modalId + ' .vxlanAlertContainer');
    const alertId = `alert-${Date.now()}`;

    const alertHTML = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Закрыть"></button>
        </div>
    `;

    alertContainer.append(alertHTML);

    setTimeout(() => {
        $(`#${alertId}`).alert('close');
    }, 5000);
}