const ConfigRSTP = function (currentDevice) {

    const buttonScript = document.getElementById('config_button_rstp_script');
    const modalScript  = document.getElementById('config_modal_rstp_script');
    const switchNameContainer = document.getElementById('config_switch_name');

    if (!buttonScript || !modalScript || !switchNameContainer) {
        console.warn("STP config elements not found, skipping ConfigRSTP setup");
        return;
    }

    var modalId = 'RstpModal_' + currentDevice.data.id;

    // Guard before using innerHTML
    var buttonHTML = buttonScript.innerHTML || '';
    if (!buttonHTML.trim()) {
        console.warn("Button HTML is empty, skipping");
        return;
    }
    var buttonElem = $(buttonHTML).appendTo('#config_switch_name');
    if (!buttonElem || buttonElem.length === 0) return;
    buttonElem.val(currentDevice.config.stp);
    buttonElem.attr('data-bs-target', '#' + modalId);

    // Remove old modal if it exists
    if ($('#' + modalId).length) {
        $('#' + modalId).remove();
    }

    var modalHTML = modalScript.innerHTML || '';
    if (!modalHTML.trim()) {
        console.warn("Modal HTML is empty, skipping");
        return;
    }
    modalHTML = modalHTML.replace('id="RstpModal"', 'id="' + modalId + '"');
    $(modalHTML).appendTo('body');

    $(document).ready(function () {
        if ($('[data-bs-toggle="tooltip"]').length) {
            $('[data-bs-toggle="tooltip"]').tooltip();
        }
        eventHandlers(currentDevice, modalId);
    });
};

function eventHandlers(currentDevice, modalId) {
    if (!$('#' + modalId).length) return;

    $('#' + modalId).find('#rstpConfigurationCancelIcon, #rstpConfigurationCancel').on('click', function () {
        $('#' + modalId).modal('hide');
    });

    var modalRadios = '#' + modalId + " input[type='radio'][name='config_rstp_stp']";
    if ($(modalRadios).length) {
        $(modalRadios + "[value=\"" + currentDevice.config.stp + "\"]").attr('checked', 'checked');
    }

    if ($('#' + modalId).find('#config_stp_priority').length) {
        $('#' + modalId).find('#config_stp_priority').val(currentDevice.config.priority);
    }

    $('#' + modalId).find('#rstpConfigurationSubmit').on('click', function () {
        if (!$(modalRadios + ":checked").length) return;
        var rstp_stp_config = $(modalRadios + ":checked").val();
        $('#' + modalId).modal('hide');
        updateRstpButtonStyle(currentDevice, rstp_stp_config);

        currentDevice.config.stp = parseInt(rstp_stp_config);
        if (typeof updateMstpButtonVisibility === 'function') {
            updateMstpButtonVisibility(currentDevice);
        }

        var switch_id = currentDevice.data.id;
        if ($('#' + modalId + ' #modal_switch_id').length) {
            $('#' + modalId + ' #modal_switch_id').val(switch_id);
        }
        if ($('#' + modalId + ' #modal_net_guid').length) {
            $('#' + modalId + ' #modal_net_guid').val(network_guid);
        }

        if ($('#' + modalId).find("#form_config_rstp_stp").length) {
            var data = $('#' + modalId).find("#form_config_rstp_stp").serialize();
            UpdateSwitchConfiguration(data, switch_id);
        }
    });

    var priorityInput = $('#' + modalId + ' #input_priority_form')[0];
    if (!priorityInput) return;

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
    var btn = $('#config_button_rstp');
    var btnText = $('#config_button_rstp_text');
    if (!btn.length || !btnText.length) return;

    btn.val(rstp_stp_config);
    if (rstp_stp_config > 0) {
        if (rstp_stp_config == 1) btnText.text("STP");
        if (rstp_stp_config == 2) btnText.text("RSTP");
        if (rstp_stp_config == 3) btnText.text("MSTP");
        btn.addClass('btn-outline-primary').removeClass('btn-outline-secondary');
    } else {
        btn.removeClass('btn-outline-primary').addClass('btn-outline-secondary');
        btnText.text("STP");
    }
}
