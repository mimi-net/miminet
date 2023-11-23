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
    if (pcap_data[0]['decode_ip'] === undefined) {
        let arp = pcap_data[0]['decode_arp'].replaceAll('doublePrime', '"').replaceAll('singlePrime', "'").replaceAll('doubleslash','\\');
        make_decode(ethernet, arp);
    }
    else {
        let ip = pcap_data[0]['decode_ip'];
        let protocol = pcap_data[0][Object.keys(pcap_data[0]).at(-1)];
        make_decode_ip(ethernet, ip, protocol);
    }

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
        if (pcap_data[i - 1]['decode_ip'] === undefined) {
            let arp = pcap_data[i - 1]['decode_arp'].replaceAll('doublePrime', '"').replaceAll('singlePrime', "'").replaceAll('doubleslash','\\');
            make_decode(ethernet, arp);
        }
        else {
            var ip = pcap_data[i - 1]['decode_ip'];
            var protocol = pcap_data[i - 1][Object.keys(pcap_data[i - 1]).at(-1)];
            make_decode_ip(ethernet, ip, protocol);
        }
    };
});

function make_decode(eth, arp) {
    let ethernet = eth.split('  ');
    make_pa(ethernet[0], 1)
    let decode_div = make_div(1)
    ethernet.slice(1).forEach(function (el) {
        let decode_p = document.createElement("p");
        decode_p.innerHTML = el;
        decode_div.appendChild(decode_p);
    })
    decode.appendChild(decode_div);

    let arp_split = arp.split('  ');
    make_pa(arp_split[0], 2)
    let decode_div_arp = make_div(2)
    arp_split[1].split(',').forEach(function (el) {
        let decode_p = document.createElement("p");
        decode_p.innerHTML = el;
        decode_div_arp.appendChild(decode_p);
    })
    decode.appendChild(decode_div_arp);

}

function make_decode_ip(eth, ip, prot) {
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
    decode.style.lineHeight = 1;
}
function make_div(count) {
    var decode_div = document.createElement("div");
    decode_div.classList.add("collapse", "decode_body", "decode_width");
    decode_div.id = "collapseDecode" + count;
    return decode_div;
}