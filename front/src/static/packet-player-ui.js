// Check whether simulation is over and we can run packets
const CheckSimulation = function (simulation_id)
{
    $.ajax({
        type: 'GET',
        url: '/check_simulation?simulation_id=' + simulation_id + '&network_guid=' + network_guid,
        data: '',
        success: function(data, textStatus, xhr) {
            // If we got 210 (processing) wait 2 sec and call themself again
            if (xhr.status === 210)
            {
                setTimeout(CheckSimulation, 2000, simulation_id);
            }

            // Simulation is ended up and we can grab the packets
            if (xhr.status === 200)
            {
                packets = JSON.parse(data.packets);
                pcaps = data.pcaps;

                // Set filters
                packetsNotFiltered = null;
                SetPacketFilter();

                const answerButton = document.querySelector('button[name="answerQuestion"]');
                if (answerButton) {
                    answerButton.disabled = false;
                }
            }
        },
        error: function(xhr) {
            console.log('Cannot check simulation id = ' + simulation_id);
            if (lastSimulationId == simulation_id){
                SetNetworkPlayerState(-1);
            }
        },
        contentType: "application/json",
        dataType: 'json'
    });
}

const InsertWaitingTime = function ()
{
    // Get last emulation task time
    // and send request to get count of emulating networks before this time
    $.ajax({
        type: 'GET',
        url: 'emulation_queue/time',
        data: '',
        success: function(data) {
            // Run helper function with time param
            InsertWaitingTimeHelper(data.time)
        },
        error: function(err) {
            console.error("Failed to fetch queue time:", err);
        },
        contentType: "application/json",
        dataType: 'json'
    });
}

const InsertWaitingTimeHelper = function(time_filter) {
    // Insert field with queue size
    $.ajax({
        type: 'GET',
        url: 'emulation_queue/size?time-filter=' + time_filter.toString(),
        data: '',
        success: function(data) {
            const queue_size = parseInt(data.size);
            if (!$('#NetworkPlayer button:first').prop('disabled')) {
                console.log($('#NetworkPlayer button:first').prop('disabled'))
                return;
            } else if (queue_size <= 1) {
                $('#NetworkPlayerLabel').text("Ожидание 10-15 сек.");
            } else {
                $('#NetworkPlayerLabel').text(`Место в очереди ${queue_size}`);

                // Update waiting time
                setTimeout(() => InsertWaitingTimeHelper(time_filter), 500);
            }

        },
        error: function(err) {
            console.error("Failed to fetch queue size:", err);
        },
        contentType: "application/json",
        dataType: 'json'
    });
}

const RunSimulation = function (network_guid)
{
    $.ajax({
        type: 'POST',
        url: '/run_simulation?guid=' + network_guid,
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
