const TakeGraphPictureAndUpdate = function()
{
    if (!global_cy)
    {
        return;
    }

    let png_blob = global_cy.png({output: 'blob', maxWidth: 512, maxHeight: 512});

    $.ajax({
        type: 'POST',
        url: '/network/upload_network_picture?guid=' + network_guid,
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

    $.ajax({
        type: 'POST',
        url: '/network/update_network_config?guid=' + network_guid,
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
    $.ajax({
        type: 'POST',
        url: '/network/copy_network?guid=' + network_guid,
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
