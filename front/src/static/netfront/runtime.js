const RunSimulation = function (network_guid)
{
    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/run_simulation?guid=' + network_guid),
        data: '',
        success: function(data, textStatus, xhr) {
            if (xhr.status === 201)
            {
                lastSimulationId = data.simulation_id
                console.log("Simulation is running!");
                // Ok, run CheckSimulation
                if (data.simulation_id)
                {
                    CheckSimulation(data.simulation_id);
                }
            }
        },
        error: function(err) {
            console.log('Cannot run simulation guid = ' + network_guid);
            SetNetworkPlayerState(-1);
        },
        contentType: "application/json",
        dataType: 'json'
    });
}

const FilterPackets = function () {
    const tcpRegex = /TCP \((ACK|SYN|FIN)/;
    packets = packets
        .map((step) =>
            step.filter(
                (pkt) =>
                    !(
                        (packetFilterState.hideARP &&
                            pkt.data.label.startsWith("ARP")) ||
                        (packetFilterState.hideSTP &&
                            (pkt.data.label.startsWith("STP") ||
                            pkt.data.label.startsWith("RSTP"))) ||
                        (packetFilterState.hideSYN &&
                            tcpRegex.test(pkt.data.label))
                    )
            )
        )
        .filter((step) => step.length > 0);
};

const UpdateFilterStates = function (settings) {
    if (!settings) {
        return;
    }

    Object.assign(packetFilterState, settings);
    $("#ARPFilterCheckbox").prop("checked", packetFilterState.hideARP);
    $("#STPFilterCheckbox").prop("checked", packetFilterState.hideSTP);
    $("#SYNFilterCheckbox").prop("checked", packetFilterState.hideSYN);
};

const SaveAnimationFilters = function () {
    if (!window.isAuthenticated) {
        return;
    }

    const payload = {
        hideARP: Boolean(packetFilterState.hideARP),
        hideSTP: Boolean(packetFilterState.hideSTP),
        hideSYN: Boolean(packetFilterState.hideSYN),
    };

    $.ajax({
        type: "POST",
        url: "/user/animation_filters",
        data: JSON.stringify(payload),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        success: function (data) {
            if (!data) {
                return;
            }

            const saved = {
                hideARP: Boolean(data.hideARP),
                hideSTP: Boolean(data.hideSTP),
                hideSYN: Boolean(data.hideSYN),
            };

            UpdateFilterStates(saved);
        },
        error: function (xhr) {
            console.log("Cannot save animation filters");
            console.log(xhr);
        },
    });
};

const SetPacketFilter = function (shared = 0) {
    // If network player UI is absent (e.g., not on network page), skip.
    if (!document.getElementById("NetworkPlayer") || !document.getElementById("PacketSliderInput")) {
        return;
    }

    console.log("Packet filter call");
    // SetPacketFilter first call on emulated network
    if (packets && !packetsNotFiltered) {
        packetsNotFiltered = JSON.parse(JSON.stringify(packets)); // Array deep copy
    }
    // Numerous filter call, we grab our packets copy to filter it
    else if (packetsNotFiltered) {
        packets = JSON.parse(JSON.stringify(packetsNotFiltered));
    }

    packetFilterState.hideARP = $("#ARPFilterCheckbox").is(":checked");
    packetFilterState.hideSTP = $("#STPFilterCheckbox").is(":checked");
    packetFilterState.hideSYN = $("#SYNFilterCheckbox").is(":checked");

    if (packets) {
        FilterPackets();
        if (shared) {
            SetSharedNetworkPlayerState();
        } else {
            SetNetworkPlayerState(0);
        }
    }
};

// 2 states:
// Do we need emulation
// We have a packets and ready to play packets
const SetNetworkPlayerState = function (simulation_id) {

    // Reset?
    if (simulation_id === -1) {
        packetsNotFiltered = null;
        packets = null;
        pcaps = [];
        SetNetworkPlayerState(0);
        return;
    }

    // If we have packets, then we're ready to run
    if (packets)
    {
        $('#NetworkPlayer').empty();
        $('#NetworkPlayer').append('<button type="button" class="btn btn-danger me-2" id="NetworkStopButton"><i class="bx bx-stop fs-xl"></i></button>');
        $('#NetworkPlayer').append('<button type="button" class="btn btn-success" id="NetworkPlayPauseButton" onclick="if (typeof window.ym != \'undefined\'){ym(92293993,\'reachGoal\',\'PlayPauseButton\');}"><i class="bx bx-play fs-xl"></i></button>');

        // Init player
        PacketPlayer.getInstance().InitPlayer(packets);

        // Configure the slider
        if (!$('#PacketSliderInput')[0] || !$('#PacketSliderInput')[0].noUiSlider) {
            return;
        }

        $('#PacketSliderInput')[0].noUiSlider.updateOptions({
            start: [1],
            range: {
                'min': 1,
                'max': packets.length,
            },
            format: {
                to: function (val){return '' + val},
                from: function (val){return '' + val},
            },
            tooltips: false,
        });

        // Show Slider on
        $('#PacketSliderInput').show();

        const pkt_count = packets.reduce((currentCount, row) => currentCount + row.length, 0);
        $('#NetworkPlayerLabel').text(packets.length + ' ' + NumWord(packets.length, ['шаг', 'шага', 'шагов']) + ' / ' + pkt_count + ' ' + NumWord(pkt_count, ['пакет', 'пакета', 'пакетов']));

        $('#PacketSliderInput')[0].noUiSlider.on('slide', function (e) {
            if (!e) return;
            let x =  Math.round(e[0]);
            PacketPlayer.getInstance().setAnimationTrafficStep(x-1);
        });

        $('#PacketSliderInput')[0].noUiSlider.on('update', function (e) {
            if (!e) return;
            let x =  Math.round(e[0]);
            if (packets.length === 0){
                $('#NetworkPlayerLabel').text('0 пакетов');
                return;
            }
            $('#NetworkPlayerLabel').text('Шаг: ' + x + '/' + packets.length + ' (' +  packets[x-1].length + ' ' + NumWord(packets[x-1].length, ['пакет', 'пакета', 'пакетов']) + ')');
        });

        // Set click handlers
        $('#NetworkPlayPauseButton').click(function() {

            // If btn-success then start to play
            if ($(this).hasClass("btn-success")){
                $(this).removeClass('btn-success');
                $(this).addClass('btn-warning');

                $(this).empty();
                $(this).append('<i class="bx bx-pause fs-xl"></i>');

                // If not in pause. Draw a new layout and go.
                if (!PacketPlayer.getInstance().getPlayerPause())
                {
                    DrawGraphStatic(nodes, edges);
                }

                PacketPlayer.getInstance().setAnimationTrafficStepCallback(function() {
                    $('#PacketSliderInput')[0].noUiSlider.set(PacketPlayer.getInstance().getAnimationTrafficStep());
                });

                PacketPlayer.getInstance().StartPlayer(global_cy);
                return;
            } else {

                $(this).removeClass('btn-warning');
                $(this).addClass('btn-success');
                $(this).empty();
                $(this).append('<i class="bx bx-play fs-xl"></i>');

                PacketPlayer.getInstance().PausePlayer();
                return;
            }
        });

        $('#NetworkStopButton').click(function() {

            PacketPlayer.getInstance().resetAnimationTrafficStepCallback();
            PacketPlayer.getInstance().StopPlayer();

            // Reset slider.
            $('#PacketSliderInput')[0].noUiSlider.set(0);

            DrawGraph(nodes, edges);

            $('#NetworkPlayPauseButton').removeClass('btn-success');
            $('#NetworkPlayPauseButton').removeClass('btn-warning');
            $('#NetworkPlayPauseButton').empty();
            $('#NetworkPlayPauseButton').addClass('btn-success');
            $('#NetworkPlayPauseButton').append('<i class="bx bx-play fs-xl"></i>');
            return;
        });

        return;
    }

    // No packets.
    // The network is simulating?
    if (simulation_id) {
        $('#NetworkPlayer').empty();
        $('#PacketSliderInput').hide();
        $('#NetworkPlayer').append('<button type="button" class="btn btn-primary w-100" id="NetworkEmulateButton" disabled>Эмулируется...</button>');
        InsertWaitingTime()
        CheckSimulation(simulation_id);
        return;
    }

    // No packets and no simulation.
    // Add emulation button.
    $('#NetworkPlayer').empty();
    $('#PacketSliderInput').hide();
    $('#NetworkPlayer').append('<button type="button" class="btn btn-primary w-100" id="NetworkEmulateButton">Эмулировать</button>');
    $('#NetworkPlayerLabel').empty();

    $('#NetworkEmulateButton').click(function() {

        // Check for job. If no job - show modal and exit.
        if (!jobs.length)
        {
            $('#noJobsModal').modal('toggle');
            return;
        }

        if (nodes.length > 80)
        {
            $('#tooManyHostModal').modal('toggle');
            return;
        }

        if (typeof window.ym != 'undefined')
        {
            ym(92293993,'reachGoal','NetworkEmulate');
        }

        RunSimulation(network_guid);

        $('#NetworkPlayer').empty();
        $('#NetworkPlayer').append('<button type="button" class="btn btn-primary w-100" id="NetworkEmulateButton" disabled>Эмулируется...</button>');
        InsertWaitingTime();
        return;
    });

    return;

}

// 2 states:
// No packets - disable button.
// We have a packets and ready to play packets
const SetSharedNetworkPlayerState = function()
{

    // If we have packets, then we're ready to run
    if (packets)
    {
        $('#NetworkPlayer').empty();
        $('#NetworkPlayer').append('<button type="button" class="btn btn-danger me-2" id="NetworkStopButton"><i class="bx bx-stop fs-xl"></i></button>');
        $('#NetworkPlayer').append('<button type="button" class="btn btn-success" id="NetworkPlayPauseButton" onclick="if (typeof window.ym != \'undefined\'){ym(92293993,\'reachGoal\',\'PlayPauseButton\');}"><i class="bx bx-play fs-xl"></i></button>');

        // Init player
        PacketPlayer.getInstance().InitPlayer(packets);

        // Configure the slider
        $('#PacketSliderInput')[0].noUiSlider.updateOptions({
            start: [1],
            range: {
                'min': 1,
                'max': packets.length,
            },
            format: {
                to: function (val){return '' + val},
                from: function (val){return '' + val},
            },
            tooltips: false,
        });

        // Show Slider on
        $('#PacketSliderInput').show();

        const pkt_count = packets.reduce((currentCount, row) => currentCount + row.length, 0);
        $('#NetworkPlayerLabel').text(packets.length + ' ' + NumWord(packets.length, ['шаг', 'шага', 'шагов']) + ' / ' + pkt_count + ' ' + NumWord(pkt_count, ['пакет', 'пакета', 'пакетов']));

        $('#PacketSliderInput')[0].noUiSlider.on('slide', function (e) {
            if (!e) return;
            let x =  Math.round(e[0]);
            PacketPlayer.getInstance().setAnimationTrafficStep(x-1);
        });

        $('#PacketSliderInput')[0].noUiSlider.on('update', function (e) {
            if (!e) return;
            let x =  Math.round(e[0]);
            if (packets.length === 0){
                $('#NetworkPlayerLabel').text('0 пакетов');
                return;
            }
            $('#NetworkPlayerLabel').text('Шаг: ' + x + '/' + packets.length + ' (' +  packets[x-1].length + ' ' + NumWord(packets[x-1].length, ['пакет', 'пакета', 'пакетов']) + ')');
        });

        // Set click handlers
        $('#NetworkPlayPauseButton').click(function() {

            // If btn-success then start to play
            if ($(this).hasClass("btn-success")){
                $(this).removeClass('btn-success');
                $(this).addClass('btn-warning');

                $(this).empty();
                $(this).append('<i class="bx bx-pause fs-xl"></i>');

                // If not in pause. Draw a new layout and go.
                if (!PacketPlayer.getInstance().getPlayerPause())
                {
                    DrawGraphStatic(nodes, edges);
                }

                PacketPlayer.getInstance().setAnimationTrafficStepCallback(function() {
                    $('#PacketSliderInput')[0].noUiSlider.set(PacketPlayer.getInstance().getAnimationTrafficStep());
                });

                PacketPlayer.getInstance().StartPlayer(global_cy);
            } else {
                $(this).removeClass('btn-warning');
                $(this).addClass('btn-success');
                $(this).empty();
                $(this).append('<i class="bx bx-play fs-xl"></i>');

                PacketPlayer.getInstance().PausePlayer();
                return;
            }
        });

        $('#NetworkStopButton').click(function() {

            PacketPlayer.getInstance().resetAnimationTrafficStepCallback();
            PacketPlayer.getInstance().StopPlayer();

            // Reset slider.
            $('#PacketSliderInput')[0].noUiSlider.set(0);

            DrawSharedGraph(nodes, edges);

            $('#NetworkPlayPauseButton').removeClass('btn-success');
            $('#NetworkPlayPauseButton').removeClass('btn-warning');
            $('#NetworkPlayPauseButton').empty();
            $('#NetworkPlayPauseButton').addClass('btn-success');
            $('#NetworkPlayPauseButton').append('<i class="bx bx-play fs-xl"></i>');
            return;
        });

        return;
    }

    // No packets
    // Add info button
    $('#NetworkPlayer').empty();
    $('#PacketSliderInput').hide();
    $('#NetworkPlayerLabel').empty();
    $('#NetworkPlayer').append('<button type="button" class="btn btn-primary w-100" id="NetworkEmulateButton" disabled>Нет эмуляции</button>');
    return;
}

// Take a picture and update it.
const TakeGraphPictureAndUpdate = function()
{
    if (!global_cy)
    {
        return;
    }

    let png_blob = global_cy.png({output: 'blob', maxWidth: 512, maxHeight: 512});

    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/network/upload_network_picture?guid=' + network_guid),
        data: png_blob,
        processData: false,
        error: function(xhr) {

            if (xhr.status != 200){
                console.log('Cannot upload graph picture');
            }

        },
        dataType: 'image/png'
    });
}

// Calculate drop offsets
const CalculateDropOffset = function(elem_x, elem_y)
{
    const network_scheme = document.getElementById("network_scheme");
    let offset_left = 0;
    let offset_top = 0;
    let ret = {'x' : 0, 'y' : 0};

    console.log(elem_x + ", " + elem_y);

    if (network_scheme){
        ret.x += network_scheme.offsetLeft - 25;
        ret.y += network_scheme.offsetTop - 15;
    }

    if (global_cy)
    {
        ret.x = ret.x + global_cy.pan().x;
        ret.y = ret.y + global_cy.pan().y;

        ret.x = (elem_x - ret.x) / global_cy.zoom();
        ret.y = (elem_y - ret.y) / global_cy.zoom();
        
        // Apply snap-to-grid
        const baseGridSize = 25;
        ret.x = Math.round(ret.x / baseGridSize) * baseGridSize;
        ret.y = Math.round(ret.y / baseGridSize) * baseGridSize;
    }

    return ret;
}

const UpdateNetworkConfig = function()
{
    if (!global_cy){
        return;
    }

    let data = {'network_title' : network_title, 'network_description' : network_description,
    'zoom' : global_cy.zoom(),'pan_x' : global_cy.pan().x, 'pan_y' : global_cy.pan().y};

    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/network/update_network_config?guid=' + network_guid),
        data: JSON.stringify(data),
        contentType: "application/json; charset=utf-8",
        success: function(data, textStatus, xhr) {
        },
        error: function(xhr) {
            console.log('Cannot update network config');
            console.log(xhr);
        },
        dataType: 'json'
    });

}

const CopyNetwork = function ()
{
    ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/network/copy_network?guid=' + network_guid),
        data: '',
        success: function(data, textStatus, xhr) {
            if (xhr.status === 200)
            {
                console.log("Copy network is made.");
                $('#ModalCopy').modal('show');
                $('.modal-option').click(function() {
                var selectedOption = $(this).attr('data-option');
                    if (selectedOption === 'edit') {
                        var newUrl = data.new_url;
                        window.location.href = newUrl;
                        console.log('Go to editing');
                    } else if (selectedOption === 'continue') {
                        console.log('Continue here');
                    }
                $('#ModalCopy').modal('hide');
                });
            }
        },
        error: function(err) {
            console.log('Copy has not been made.');
        },
        contentType: "application/json",
        dataType: 'json'
    });
}


const NumWord = function (value, words){
    value = Math.abs(value) % 100;
    var num = value % 10;
    if(value > 10 && value < 20) return words[2];
    if(num > 1 && num < 5) return words[1];
    if(num == 1) return words[0];
    return words[2];
}

const SaveNetworkObject = function (){
    let n = JSON.parse(JSON.stringify(nodes));
    let e = JSON.parse(JSON.stringify(edges));

    NetworkCache.push({
        nodes: n,
        edges: e,
    });

    return 0;
}

const RestoreNetworkObject = function (){
    let x = NetworkCache.pop();

    if (!x){
        return;
    }

    nodes=x.nodes;
    edges=x.edges;

    return 0;
}

// ========== COMMAND EDITING UTILITIES ==========
// Global variables to track editing state
let editingJobId = null;
let editingDeviceType = null;

// Function to enter edit mode
const EnterEditMode = function(deviceType, jobId, jobTypeId) {
    editingJobId = jobId;
    editingDeviceType = deviceType;

    // Change submit button text
    const submitButton = document.getElementById(`config_${deviceType}_main_form_submit_button`);
    if (submitButton) {
        submitButton.textContent = 'Сохранить изменения';
    }

    // Change label text from "Выполнить команду" to "Редактировать команду"
    const selectLabel = $(`label[for="config_${deviceType}_job_select_field"]`);
    if (selectLabel.length) {
        selectLabel.text('Редактировать команду');
    }

    // Hide the select dropdown and show command name
    const selectField = document.getElementById(`config_${deviceType}_job_select_field`);
    if (selectField) {
        selectField.style.display = 'none';

        // Remove old command display if exists
        const existingDisplay = document.getElementById(`config_${deviceType}_edit_command_display`);
        if (existingDisplay) {
            existingDisplay.remove();
        }

        // Get command name from the selected option in HTML
        const selectedOption = selectField.querySelector(`option[value="${jobTypeId}"]`);
        const commandName = selectedOption ? selectedOption.textContent : 'Команда';

        // Create and insert command name display
        const commandDisplay = document.createElement('input');
        commandDisplay.type = 'text';
        commandDisplay.id = `config_${deviceType}_edit_command_display`;
        commandDisplay.className = 'form-control form-control-sm';
        commandDisplay.value = commandName;
        commandDisplay.disabled = true;
        selectField.parentNode.insertBefore(commandDisplay, selectField.nextSibling);
    }

    // Highlight the editing command
    $(`#config_${deviceType}_job_list li`).removeClass('editing-command');
    const listItem = $(`#config_${deviceType}_job_delete_${jobId}`).closest('li');
    listItem.addClass('editing-command');

    // Highlight only the input fields area after it's inserted into DOM
    setTimeout(() => {
        const jobList = document.getElementById(`config_${deviceType}_job_list`);
        if (jobList) {
            const inputDiv = $(jobList).prev(`div[name="config_${deviceType}_select_input"]`);
            if (inputDiv.length) {
                inputDiv.addClass('editing-form-area');
            }
        }

        // Scroll to the "Редактировать команду" label (select field)
        // This helps when user clicks edit on a command at the bottom of the list
        const selectLabel = $(`label[for="config_${deviceType}_job_select_field"]`);
        if (selectLabel.length) {
            selectLabel[0].scrollIntoView({
                behavior: 'smooth',
                block: 'start',
                inline: 'nearest'
            });
        }
    }, 50);
};

// Function to exit edit mode
const ExitEditMode = function(deviceType) {
    editingJobId = null;
    editingDeviceType = null;

    // Reset submit button text
    const submitButton = document.getElementById(`config_${deviceType}_main_form_submit_button`);
    if (submitButton) {
        submitButton.textContent = 'Сохранить';
    }

    // Reset label text back to "Выполнить команду"
    const selectLabel = $(`label[for="config_${deviceType}_job_select_field"]`);
    if (selectLabel.length) {
        selectLabel.text('Выполнить команду');
    }

    // Remove command text display
    const commandDisplay = document.getElementById(`config_${deviceType}_edit_command_display`);
    if (commandDisplay) {
        commandDisplay.remove();
    }

    // Show the select dropdown again
    const selectField = document.getElementById(`config_${deviceType}_job_select_field`);
    if (selectField) {
        selectField.style.display = 'block';
        selectField.value = '0';
    }

    // Remove highlight from command and input areas
    $(`#config_${deviceType}_job_list li`).removeClass('editing-command');
    $(`div[name="config_${deviceType}_select_input"]`).removeClass('editing-form-area');

    // Clear form inputs
    $('div[name="config_' + deviceType + '_select_input"]').remove();
};

// Function to delete old job and save new configuration
const DeleteAndSaveJob = function(deviceType, updateFunction, formData, deviceId) {
    if (!editingJobId || editingDeviceType !== deviceType) {
        // Not in edit mode, just save
        updateFunction(formData, deviceId);
        return;
    }

    // In edit mode: pass editing_job_id to server
    // Server will validate first, then delete old and add new atomically
    formData += '&editing_job_id=' + encodeURIComponent(editingJobId);

    updateFunction(formData, deviceId);
};

// Grid drawing functions
const initGrid = function(cy) {
    if (!cy) return;

    // Clean up previous listener
    if (typeof gridCanvasLayer !== 'undefined' && gridCanvasLayer && gridCanvasLayer.resizeAndDrawCanvas) {
        window.removeEventListener('resize', gridCanvasLayer.resizeAndDrawCanvas);
    }

    // Remove old grid canvas if exists
    const oldCanvas = document.getElementById('grid-canvas-static');
    if (oldCanvas) {
        oldCanvas.remove();
    }

    // Create canvas with absolute positioning to overlay on top of cytoscape container
    const canvas = document.createElement('canvas');
    canvas.id = 'grid-canvas-static';
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.pointerEvents = 'none';

    const container = cy.container();
    container.insertBefore(canvas, container.firstChild);

    const ctx = canvas.getContext('2d');

    const resizeAndDrawCanvas = function() {
        const pixelRatio = window.devicePixelRatio || 1;
        
        // Use container dimensions instead of window dimensions to prevent distortion
        // when container is not full screen
        canvas.width = container.clientWidth * pixelRatio;
        canvas.height = container.clientHeight * pixelRatio;

        // Always redraw when resizing
        if (gridCanvasLayer) {
            drawGrid();
        }
    };

    gridCanvasLayer = {
        canvas: canvas,
        ctx: ctx,
        resizeAndDrawCanvas: resizeAndDrawCanvas
    };

    resizeAndDrawCanvas();

    // Add event listener for resize
    window.addEventListener('resize', resizeAndDrawCanvas);

    // Add cy resize listener to handle container resizing specifically
    if (cy) {
        cy.on('resize', resizeAndDrawCanvas);
    }

    // Initialize current zoom from cytoscape
    if (cy && cy.zoom) {
        currentGridZoom = cy.zoom();
    }

    // Draw grid
    drawGrid();
};

const drawGrid = function() {
    if (!gridCanvasLayer) {
        return;
    }

    const canvas = gridCanvasLayer.canvas;
    const ctx = gridCanvasLayer.ctx;

    if (!canvas || !ctx) {
        return;
    }

    // Scale grid with zoom: at max zoom (2.0) = 50px like before, at min zoom (0.5) = small cells
    const gridSize = 25 * currentGridZoom; // 25 * 2.0 = 50px (max zoom), 25 * 0.5 = 12.5px (min zoom)
    const pixelRatio = window.devicePixelRatio || 1;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const screenWidth = canvas.width / pixelRatio;
    const screenHeight = canvas.height / pixelRatio;

    // Get pan offset to align grid with cytoscape coordinate system
    let panX = 0;
    let panY = 0;
    if (global_cy && global_cy.pan) {
        const pan = global_cy.pan();
        panX = pan.x;
        panY = pan.y;
    }

    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);

    // Draw grid lines across entire viewport
    ctx.strokeStyle = 'rgba(200, 200, 200, 0.4)';
    ctx.lineWidth = 1;

    ctx.beginPath();

    // Calculate grid origin with pan offset
    // Grid should be offset by pan to stay aligned with nodes
    const gridOriginX = panX % gridSize;
    const gridOriginY = panY % gridSize;

    // Vertical lines across entire viewport
    let verticalCount = 0;
    const startX = Math.floor(-gridOriginX / gridSize) * gridSize + gridOriginX;
    for (let x = startX; x <= screenWidth; x += gridSize) {
        ctx.moveTo(x, 0);
        ctx.lineTo(x, screenHeight);
        verticalCount++;
    }

    // Horizontal lines across entire viewport
    let horizontalCount = 0;
    const startY = Math.floor(-gridOriginY / gridSize) * gridSize + gridOriginY;
    for (let y = startY; y <= screenHeight; y += gridSize) {
        ctx.moveTo(0, y);
        ctx.lineTo(screenWidth, y);
        horizontalCount++;
    }

    ctx.stroke();
};


// Update grid when config panel opens/closes
const updateGridForConfigPanel = function() {
    if (gridCanvasLayer && gridCanvasLayer.resizeAndDrawCanvas) {
        // Small delay to let DOM update
        setTimeout(function() {
            gridCanvasLayer.resizeAndDrawCanvas();
        }, 50);
    }
}
