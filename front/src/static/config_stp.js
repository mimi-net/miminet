const ConfigRSTP = function (currentDevice) {
    var modalId = 'RstpModal_' + currentDevice.data.id;

    var buttonHTML = document.getElementById('config_button_rstp_script').innerHTML;
    var buttonElem = $(buttonHTML).appendTo('#config_switch_name');
    buttonElem.val(currentDevice.config.stp);
    buttonElem.attr('data-bs-target', '#' + modalId);

    $('#' + modalId).remove();
    var modalHTML = document.getElementById('config_modal_rstp_script').innerHTML;
    modalHTML = modalHTML.replace('id="RstpModal"', 'id="' + modalId + '"');
    var modalElem = $(modalHTML).appendTo('body');

    $(document).ready(function () {
        $('[data-bs-toggle="tooltip"]').tooltip();
        eventHandlers(currentDevice, modalId);
    });
};

function eventHandlers(currentDevice, modalId) {
    $('#' + modalId).find('#rstpConfigrationCancelIcon, #rstpConfigrationCancel').on('click', function () {
        $('#' + modalId).modal('hide');
    });
    var modalRadios = '#' + modalId + " input[type='radio'][name='config_rstp_stp']";
    $(modalRadios + "[value=\""+currentDevice.config.stp+"\"]").attr('checked','checked')
    $('#' + modalId).find('#config_stp_priority').val(currentDevice.config.priority)

    $('#' + modalId).find('#rstpConfigrationSubmit').on('click', function () {
        var rstp_stp_config = $(modalRadios + ":checked").val();
        $('#' + modalId).modal('hide');
        updateRstpButtonStyle(currentDevice, rstp_stp_config);

        var switch_id = currentDevice.data.id;
        $('#' + modalId + ' #modal_switch_id').val(switch_id);
        $('#' + modalId + ' #modal_net_guid').val(network_guid);

        var data = $('#' + modalId).find("#form_config_rstp_stp").serialize();
        UpdateSwitchConfiguration(data, switch_id);
    });

    var priorityInput = $('#' + modalId + ' #input_priority_form')[0];

    document.querySelectorAll(modalRadios).forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.value === '0') {
                priorityInput.style.display = 'none';
            } else {
                priorityInput.style.display = 'block';
            }
        });
    });

    if (currentDevice.config.stp > 0) {
        priorityInput.style.display = 'block';
    } else {
        priorityInput.style.display = 'none';
    }
    updateRstpButtonStyle(currentDevice, currentDevice.config.stp);
}

function updateRstpButtonStyle(currentDevice, rstp_stp_config) {
    $('#config_button_rstp').val(rstp_stp_config);
    if (rstp_stp_config > 0) {
        if (rstp_stp_config == 1) {
            $('#config_button_rstp_text').text("STP")
        }
        if (rstp_stp_config == 2) {
            $('#config_button_rstp_text').text("RSTP")
        }
        $('#config_button_rstp').addClass('btn-outline-primary').removeClass('btn-outline-secondary');
    } else {
        $('#config_button_rstp').removeClass('btn-outline-primary').addClass('btn-outline-secondary');
        $('#config_button_rstp_text').text("STP")
    }
}
