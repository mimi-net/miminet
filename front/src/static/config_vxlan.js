const ConfigVxlan = function (currentDevice) {
    var modalId = 'VxlanConfigModal' + currentDevice.data.id;
    var tableId = 'VxlanConfigTable' + currentDevice.data.id;

    $('#' + modalId).remove();

    var buttonHTML = document.getElementById('config_button_vxlan_script').innerHTML;
    var modalHTML = document.getElementById('config_modal_vxlan_script').innerHTML;
    var tableHTML = document.getElementById('config_table_vxlan_script').innerHTML;

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
        console.log("check check");
        if ($(this).is(':checked')) {
            $('#' + tableId).show();
            // generateVxlanTableContent(currentDevice, tableId);
            let ifaceToDeviseList = getInterfaceAndConnectedNodes(currentDevice);
            generateDropdownMenues(tableId, ifaceToDeviseList);
            generateNetworkInterfacesContent(tableId, ifaceToDeviseList);
            generateClientsContent(tableId, ifaceToDeviseList);
            console.log("checked");
        } else {
            resetVxlanInterfaceFields(currentDevice);
            restoreVxlanFormData(tableId);
            console.log("unchecked")
            $('#' + tableId).hide();
        }
    });

    $('#' + modalId).find('#vxlanConfigrationCancelIcon').on('click', function () {
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
        addClientVxlanInterface(currentDevice, tableId);
        console.log(currentDevice)
        let ifaceToDeviseList = getInterfaceAndConnectedNodes(currentDevice);
        generateClientsContent(tableId, ifaceToDeviseList);
    });

    $('#' + tableId).find('.add-network-vxlan-interface').off('click').on('click', function () {
        addNetworkVxlanInterface(currentDevice, tableId);
        let ifaceToDeviseList = getInterfaceAndConnectedNodes(currentDevice);
        generateNetworkInterfacesContent(tableId, ifaceToDeviseList);
    });

    updateVxlanButtonStyle(currentDevice);
}

// function createEdgeAndNodeMaps(edges, nodes) {
//     const edgesMap = new Map();
//     for (var i = 0; i < edges.length; i++) {
//         edgesMap.set(edges[i].data.id, edges[i]);
//     }

//     const nodesMap = new Map();
//     for (var i = 0; i < nodes.length; i++) {
//         nodesMap.set(nodes[i].data.id, nodes[i].data.label);
//     }

//     return { edgesMap, nodesMap };
// }

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
        devices_list.appendChild(row)}
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
            const row = createNetIfaceRow(iface,connectedNode, targetIpList[j][0], targetIpList[j][1], tableId);
            interfaces_list.appendChild(row)
            }
        }
    });

    // for (var i = 0; i < currentDevice.interface.length; i++) {
    //     let interface = currentDevice.interface[i];
    //     var connectedEdge = edgesMap.get(interface.connect);
    //     if (connectedEdge !== undefined) {
    //         let targetDeviceId = connectedEdge.data.target;
    //         if (connectedEdge.data.source === currentDevice.data.id) {
    //             targetDeviceId = connectedEdge.data.target;
    //         } else {
    //             targetDeviceId = connectedEdge.data.source;
    //         }
    //         var connectionType = interface.vxlan_connection_type;
    //         let targetIp = interface.vxlan_vni_to_target_ip;

    //         if (connectionType === 1 && targetIp !== null && targetIp !== undefined && targetIp) {
    //             for (let j = 0; j < targetIp.length; j++) {
    //                 const networkRow = document.createElement('li');
    //                 networkRow.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center', 'network-interface');
    //                 networkRow.dataset.id = interface.id;
    //                 networkRow.textContent = `Линк к: ${nodesMap.get(targetDeviceId)}, VNI: ${targetIp[j][0]}, Удаленный IP: ${targetIp[j][1]}`;
    //                 const removeButton = document.createElement('button');
    //                 removeButton.classList.add('btn', 'btn-danger', 'btn-sm');
    //                 removeButton.textContent = 'Удалить';
    //                 removeButton.onclick = function () {
    //                     removeInterface(interface, targetIp[j][1], targetIp[j][0], tableId);
    //                 };
    //                 networkRow.appendChild(removeButton);
    //                 interfaces_list.appendChild(networkRow);
    //             }
    //         }
    //     }
    // }
}

function generateDropdownMenues(tableId, ifaceToDeviseList){
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

// function generateVxlanTableContent(currentDevice, tableId) {

//     var edgesMap = new Map();
//     for (var i = 0; i < edges.length; i++) {
//         edgesMap.set(edges[i].data.id, edges[i]);
//     }

//     var nodesMap = new Map();
//     for (var i = 0; i < nodes.length; i++) {
//         nodesMap.set(nodes[i].data.id, nodes[i].data.label);
//     }

//     const select_client_link = $('#' + tableId).find('.client-device')[0];
//     const select_out_link = $('#' + tableId).find('.out-interface')[0];
//     const devices_list = $('#' + tableId).find('.devices-list')[0];
//     const interfaces_list = $('#' + tableId).find('.interfaces-list')[0];

//     // Очистка выпадающих списков
//     while (select_client_link.firstChild) {
//         select_client_link.removeChild(select_client_link.firstChild);
//     }
//     while (select_out_link.firstChild) {
//         select_out_link.removeChild(select_out_link.firstChild);
//     }

//     // Очистка списков девайсов и интерфейсов
//     while (devices_list.firstChild) {
//         devices_list.removeChild(devices_list.firstChild);
//     }
//     while (interfaces_list.firstChild) {
//         interfaces_list.removeChild(interfaces_list.firstChild);
//     }


//     for (var i = 0; i < currentDevice.interface.length; i++) {
//         let iface = currentDevice.interface[i];
//         var connectedEdge = edgesMap.get(iface.connect);
//         if (connectedEdge !== undefined) {
//             let targetDeviceId = connectedEdge.data.target;
//             if (connectedEdge.data.source === currentDevice.data.id) {
//                 targetDeviceId = connectedEdge.data.target;
//             } else {
//                 targetDeviceId = connectedEdge.data.source;
//             }
//             var vni = iface.vxlan_vni
//             var connectionType = iface.vxlan_connection_type;
//             let targetIp = iface.vxlan_vni_to_target_ip;


//             const option = document.createElement('option');
//             option.value = iface.id;
//             option.textContent = nodesMap.get(targetDeviceId);
//             select_client_link.appendChild(option);

//             const option2 = document.createElement('option');
//             option2.value = iface.id;
//             option2.textContent = nodesMap.get(targetDeviceId);
//             select_out_link.appendChild(option2);


//             if (vni !== null && vni !== undefined && connectionType === 0) {
//                 const clientRow = document.createElement('li');
//                 clientRow.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center', 'client-interface');
//                 clientRow.dataset.id = iface.id;
//                 clientRow.textContent = `Линк к: ${nodesMap.get(targetDeviceId)}, VNI: ${iface.vxlan_vni}`;
//                 const removeButton = document.createElement('button');
//                 removeButton.classList.add('btn', 'btn-danger', 'btn-sm');
//                 removeButton.textContent = 'Удалить';
//                 removeButton.onclick = function () {
//                     console.log("removing")
//                     removeDevice(iface, tableId);
//                 };
//                 clientRow.appendChild(removeButton);
//                 devices_list.appendChild(clientRow);
//             }
//             if (connectionType === 1 && targetIp !== null && targetIp !== undefined && targetIp) {
//                 for (let j = 0; j < targetIp.length; j++) {
//                     const networkRow = document.createElement('li');
//                     networkRow.classList.add('list-group-item', 'd-flex', 'justify-content-between', 'align-items-center', 'network-interface');
//                     networkRow.dataset.id = iface.id;
//                     networkRow.textContent = `Линк к: ${nodesMap.get(targetDeviceId)}, VNI: ${targetIp[j][0]}, Удаленный IP: ${targetIp[j][1]}`;
//                     const removeButton = document.createElement('button');
//                     removeButton.classList.add('btn', 'btn-danger', 'btn-sm');
//                     removeButton.textContent = 'Удалить';
//                     removeButton.onclick = function () {
//                         removeInterface(iface, targetIp[j][1], targetIp[j][0], tableId);
//                     };
//                     networkRow.appendChild(removeButton);
//                     interfaces_list.appendChild(networkRow);
//                 }
//             }
//         }
//     }
// }

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
        console.log("removing")
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


function addClientVxlanInterface(currentDevice, tableId) {
    const vni = $('#' + tableId).find('.client-vni').val();
    let deviceEntry = $('#' + tableId).find('.client-device').find('option:selected').val();

    if (!deviceEntry) {
        showAlert("Пожалуйста, выберите клиентский интерфейс.", "warning", tableId);
        return;
    }

    if (!isValidVNI(vni)) {
        showAlert("Неверный VNI. Пожалуйста, введите число от 1 до 16777214.", "danger", tableId);
        return;
    }

    if (isLinkAlreadyAdded(currentDevice, deviceEntry, 'client')) {
        showAlert("Этот интерфейс уже используется как сетевой. Пожалуйста, выберите другой интерфейс.", "danger", tableId);
        return;
    }

    if (deviceEntry === null || deviceEntry === undefined || deviceEntry === '') {
        return;
    }
    console.log(deviceEntry)
    var iface = currentDevice.interface.find(function (item) {
        return item.id === deviceEntry;
    });
    console.log(iface)
    if (iface) {
          if (iface.vxlan_connection_type === 0 || iface.vxlan_connection_type === 1) {
            showAlert("Этот интерфейс уже имеет конфигурацию VXLAN.", "warning", tableId);
            return;
        }
        console.log("added")
        iface.vxlan_vni = Number(vni);
        iface.vxlan_connection_type = 0;
        iface.vxlan_vni_to_target_ip = null;
    }
    clearClientFields(tableId);
}

function addNetworkVxlanInterface(currentDevice, tableId) {
    const vni = $('#' + tableId).find('.network-vni').val();
    const targetIp = $('#' + tableId).find('.remote-vtep-ip').val();
    let deviceEntry = $('#' + tableId).find('.out-interface').find('option:selected').val();

    if (!deviceEntry) {
        showAlert("Пожалуйста, выберите исходящий интерфейс.", "warning", tableId);
        return;
    }

    if (!isValidVNI(vni)) {
        showAlert("Неверный VNI. Пожалуйста, введите число от 1 до 16777214.", "danger", tableId);
        return;
    }

    if (!isValidIP(targetIp)) {
        showAlert("Неверный IP-адрес. Пожалуйста, введите действительный IPv4 адрес.", "danger", tableId);
        return;
    }

    if (isLinkAlreadyAdded(currentDevice, deviceEntry, 'network')) {
        showAlert("Этот интерфейс уже используется как клиентский. Пожалуйста, выберите другой интерфейс.", "danger", tableId);
        return;
    }

    if (isDuplicateNetworkEntry(currentDevice, vni, targetIp)) {
        showAlert("Такая запись VXLAN сети уже существует.", "warning", tableId);
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
    console.log("Filled Or not")
    console.log(currentDevice.interface.some(iface => ((iface.vxlan_vni !== null && iface.vxlan_vni !== undefined) || (iface.vxlan_vni_to_target_ip !== null && iface.vxlan_vni_to_target_ip !== undefined && iface.vxlan_vni_to_target_ip.length > 0)) && (iface.vxlan_connection_type !== null && iface.vxlan_connection_type !== undefined)));
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
    console.log("removing inside")
    iface.vxlan_vni = null;
    iface.vxlan_connection_type = null;
    iface.vxlan_vni_to_target_ip = null;
    console.log(iface)

    const deviceList = $('#' + tableId).find('.devices-list')[0];
    const deviceItems = deviceList.getElementsByClassName('client-interface');

    for (let item of deviceItems) {
        if (item.dataset.id === iface.id) {
            deviceList.removeChild(item);
            console.log("item removed")
            break;
        }
    }
}

function removeInterface(iface, vni, targetIp, tableId) {
    const interfaceList = $('#' + tableId).find('.interfaces-list')[0];
    const interfaceItems = interfaceList.getElementsByClassName('network-interface');
    console.log(iface)
    console.log(Array.isArray(iface.vxlan_vni_to_target_ip))
    if (Array.isArray(iface.vxlan_vni_to_target_ip)) {
        console.log(iface.vxlan_vni_to_target_ip?.length)
        console.log(vni)
        console.log(targetIp)
        iface.vxlan_vni_to_target_ip = iface.vxlan_vni_to_target_ip.filter(item => item[0] !== vni || item[1] !== targetIp);
        console.log(iface.vxlan_vni_to_target_ip?.length)
    }

    for (let item of interfaceItems) {
        const textContent = item.textContent || item.innerText;
        if (textContent.includes(`VNI: ${vni}`) && textContent.includes(`Удаленный IP: ${targetIp}`)) {
            interfaceList.removeChild(item);
            break;
        }
    }
}

function showAlert(message, type = 'info', tableId) {
    const alertContainer = $('#vxlanAlertContainer')
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