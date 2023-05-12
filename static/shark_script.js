let newdata = data.replace(/&#39;/g, '"');
// .replace(/&#34;/g,"'");
let pcap_data = JSON.parse(newdata);
let tds = document.querySelectorAll('tbody tr');
let input = document.querySelector('#bytes');
let rows = document.querySelector('#rows');
let ascii = document.querySelector('#ascii');
let decode = document.querySelector('#decode');
{
    tds[0].classList.toggle('selected');
    tds[0].classList.add('no-hover');
    let ethernet = pcap_data[0]['decode_eth'];
    let ip = pcap_data[0]['decode_ip'];
    let protocol = pcap_data[0][Object.keys(pcap_data[0]).at(-1)];
    make_decode(ethernet, ip, protocol);

    var string = pcap_data[0]['bytes'];

    for (var b = 0; b < (string.length) / 47; b++) {
        var elem1 = document.createElement("p");
        elem1.innerHTML = b.toString().padStart(4, '0');
        rows.appendChild(elem1);
        var elem2 = document.createElement("p");
        elem2.innerHTML = pcap_data[0]['bytes'].substring(b * 47 + b, (b * 47) + 47 + b);
        input.appendChild(elem2);
        var elem3 = document.createElement("p");
        var ascii_with_prime = pcap_data[0]['ascii'].replace('doublePrime', '"').replace('singlePrime', "'");
        elem3.innerHTML = ascii_with_prime.substring(b * 16 + b, (b * 16) + 16 + b);
        ascii.appendChild(elem3);
    }
}
tds.forEach(function (item) {
    item.onclick = function () {
        tds.forEach(function (el) {
            el.classList.remove('selected');
            el.classList.remove('no-hover');
            input.replaceChildren();
            rows.replaceChildren();
            ascii.replaceChildren();
            decode.replaceChildren();
        });
        var i = this.id;
        this.classList.add('no-hover');
        this.classList.toggle('selected');
        var string = pcap_data[i - 1]['bytes'];

        for (var b = 0; b < (string.length) / 47; b++) {
            var elem1 = document.createElement("p");
            elem1.innerHTML = b.toString().padStart(4, '0');
            rows.appendChild(elem1);
            var elem2 = document.createElement("p");
            elem2.innerHTML = pcap_data[i - 1]['bytes'].substring(b * 47 + b, (b * 47) + 47 + b);
            input.appendChild(elem2);
            var elem3 = document.createElement("p");
            var ascii_with_prime = pcap_data[i - 1]['ascii'].replace('doublePrime', '"').replace('singlePrime', "'");
            elem3.innerHTML = ascii_with_prime.substring(b * 16 + b, (b * 16) + 16 + b);
            ascii.appendChild(elem3);
        }
        // var len = pcap_data[i-1]['decode'].length;
        var ethernet = pcap_data[i - 1]['decode_eth'];
        var ip = pcap_data[i - 1]['decode_ip'];
        var protocol = pcap_data[i - 1][Object.keys(pcap_data[i - 1]).at(-1)];
        make_decode(ethernet, ip, protocol);
    };
});

function make_decode(eth, ip, prot) {
    let ethernet = eth.split('  ');
    make_pa(ethernet[0], 1)
    let decode_div = make_div(1)
    ethernet.slice(1).forEach(function (el) {
        let decode_p = document.createElement("p");
        decode_p.innerHTML = el;
        decode_div.appendChild(decode_p);
    })
    decode.appendChild(decode_div);

    let ip_split = ip.split('  ');
    make_pa(ip_split[0], 2)
    let decode_div_ip = make_div(2)
    ip_split[1].split(',').forEach(function (el) {
        let decode_p = document.createElement("p");
        decode_p.innerHTML = el;
        decode_div_ip.appendChild(decode_p);
    })
    decode.appendChild(decode_div_ip);

    let prot_split = prot.split('  ');
    make_pa(prot_split[0], 3)
    let decode_div_prot = make_div(3)
    prot_split[1].split(',').forEach(function (el) {
        let decode_p = document.createElement("p");
        decode_p.innerHTML = el;
        decode_div_prot.appendChild(decode_p);
    })
    decode.appendChild(decode_div_prot);
    // var temp = [];
    // var index = [];
    // var len = li_data.length;
    // li_data.forEach(function (el) {
    //     if(el.includes("data") && !el.includes("data=b") || el.includes("Ethernet")){
    //         temp.push(el);
    //         index.push(li_data.indexOf(el));
    //     }
    // });
    // var count = 0;
    // temp.forEach(function(el){
    //     var name = el.split('(');
    //     make_pa(name[0]+'(', count);
    //     var decode_div = make_div(count);
    //     var decode_p = document.createElement("p");
    //     decode_p.innerHTML = name[1] + ',';
    //     decode_div.appendChild(decode_p);
    //     var count2 = 0;
    //     li_data.slice(index[count]+1,index[count+1]).forEach(function (data) {
    //         if (!data.includes("data=b")) {
    //             let index2 = li_data.indexOf(data);
    //             let decode_p = document.createElement("p");
    //             if(count2 == index[count+1]-index[count]-2 || li_data[index2+1].includes("data=b")){
    //                 decode_p.innerHTML = data + ' )';
    //             }
    //             else{
    //                 decode_p.innerHTML = data + ',';
    //             }
    //             decode_div.appendChild(decode_p);
    //             count2++;
    //         }

    //     });
    //     decode.appendChild(decode_div);
    //     count++;
    // });
}

function make_pa(text, count) {
    var decode_p = document.createElement("p");
    var decode_a = document.createElement("a");
    decode_a.classList.add("decode_head", "dropdown-t");
    decode_a.href = "#collapseDecode" + count;
    decode_a.setAttribute('data-bs-toggle', 'collapse');
    decode_a.setAttribute("aria-expanded", "false");
    decode_a.setAttribute("aria-controls", "collapseDecode" + count)
    decode_a.innerHTML = text;
    decode_p.appendChild(decode_a);
    decode.appendChild(decode_p);
}
function make_div(count) {
    var decode_div = document.createElement("div");
    decode_div.classList.add("collapse", "decode_body", "decode_width");
    decode_div.id = "collapseDecode" + count;
    return decode_div;
}


{/* <p>
<a class="decode_head dropdown-toggle" data-bs-toggle="collapse" href="#collapseExample"  aria-expanded="false" aria-controls="collapseExample" >
  Link with href
</a>
</p>
<div class="collapse decode_body" id="collapseExample">
  Some placeholder content for the collapse component. This panel is hidden by default but revealed when the user activates the relevant trigger.
</div>*/}




// document.querySelector('tbody').onclick = (event) => {
//     let cell = event.target;
//     // if (cell.tagName.toLowerCase() != 'td')
//     //   return;
//     let i = cell.parentNode.rowIndex;
//     let j = cell.cellIndex;
//     tds.forEach(function (el) {
//         el.classList.remove('selected');
//         el.classList.remove('no-hover');
//         input.replaceChildren();
//         rows.replaceChildren();
//     });
//     cell.parentNode.classList.add('no-hover');
//     cell.parentNode.classList.toggle('selected');
//     var string = pcap_data[i-1]['bytes'];

//     for(var b =0 ; b < (string.length)/45; b++){
//         var elem1 = document.createElement("p");
//         elem1.innerHTML = b.toString().padStart(4, '0');
//         rows.appendChild(elem1);
//         var elem2 = document.createElement("p");
//         elem2.innerHTML = pcap_data[i-1]['bytes'].substring(b*44+b,(b*44)+44+b);
//         input.appendChild(elem2);
//     }
//     // var string = pcap_data[i-1]['bytes'];
//     // input.innerHTML = string;
//     console.log(i, j);
//   }



{/* <label for="info__body_1" class="info__headline" style="text-align: left;">Frame 1: 74 bytes on wire (592
                bits), 74 bytes captured (592 bits)</label> */}