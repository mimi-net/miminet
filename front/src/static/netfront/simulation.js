const CheckSimulation = function (simulation_id)
{
    ajaxWithAuth({
        type: 'GET',
        url: ExternalUrlFor('/check_simulation?simulation_id=' + simulation_id + '&network_guid=' + network_guid),
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

// Update edge configuration
const UpdateEdgeConfiguration = (data) => {
    SetNetworkPlayerState(-1);

    return ajaxWithAuth({
        type: 'POST',
        url: ExternalUrlFor('/edge/save_config'),
        data: data,
        complete: function() {
            DrawGraph();
            $('#config_edge_main_form_submit_button').html('Сохранить');
        },
        error: function(xhr) {
            console.log('Не удалось обновить конфигурацию ребра');
            console.log(xhr);
        },
        dataType: 'json'
    });
};


const InsertWaitingTime = function ()
{
    // Get last emulation task time
    // and send request to get count of emulating networks before this time
    ajaxWithAuth({
        type: 'GET',
        url: ExternalUrlFor('/emulation_queue/time'),
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
    ajaxWithAuth({
        type: 'GET',
        url: ExternalUrlFor('/emulation_queue/size?time-filter=' + time_filter.toString()),
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

// Update host configuration
