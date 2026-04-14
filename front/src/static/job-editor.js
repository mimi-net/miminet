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
