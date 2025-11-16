let newdata = data.replace(/&#39;/g, '"'); 
let pcap_data = JSON.parse(newdata);
let tds = document.querySelectorAll('tbody tr');
let input = document.querySelector('#bytes');
let rows = document.querySelector('#rows');
let ascii = document.querySelector('#ascii');
let decode = document.querySelector('#decode');
if (tds.length > 0){
	tds[0].classList.toggle('selected');
	tds[0].classList.add('no-hover');
	decode_packet(pcap_data[0].bytes);

    // Creating div elements for byte assignments
	createByteDivs(pcap_data[0].bytes, pcap_data[0]);
    AddHoverInfoAttribute();
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

        createByteDivs(pcap_data[i - 1].bytes, pcap_data[i - 1]);
		decode_packet(pcap_data[i - 1].bytes);
        AddHoverInfoAttribute();
    };
});

function make_pa(text, count) {
    const decode_p = document.createElement('p');
    const decode_a = document.createElement('a');
    decode_a.classList.add('decode_head', 'dropdown-t');
    decode_a.href = `#collapseDecode${count}`;
    decode_a.setAttribute('data-bs-toggle', 'collapse');
    decode_a.setAttribute('aria-expanded', 'false');
    decode_a.setAttribute('aria-controls', 'collapseDecode' + count);
    decode_a.innerHTML = text;
    decode_p.appendChild(decode_a);
    decode.appendChild(decode_p);
}

function make_div(count) {
    const decode_div = document.createElement('div');
    decode_div.classList.add('collapse', 'decode_body', 'decode_width');
    decode_div.id = `collapseDecode${count}`;
    return decode_div;
}

function hex_to_ip(ip_hex) {
    const ip_str = [];
    for (let i = 0; i < ip_hex.length; i++) {
        ip_str[i] = parseInt(ip_hex[i], 16);
    }
    return ip_str.join('.');
}


function decode_ethernet_header (eth_hdr) {

	let eth_type = eth_hdr.slice(12,14).join("");
	let eth_type_length_string = "";

	if (eth_hdr.length < 14) {
		console.log("Mimishark: Ethernet header is too short");
		return {};
	}

	// Do we have LLC packet
	if (parseInt(eth_type, 16) < 1500) {
		eth_type_length_string = parseInt(eth_type, 16).toString() + " bytes";

	// Do we have ARP
	} else if (eth_type === "0806") {
		eth_type_length_string = "ARP (0x0806)";

	// Do we have IP
	} else if (eth_type === "0800") {
		eth_type_length_string = "IPv4 (0x0800)"
	}

    return {
        'Destination:': { value: eth_hdr.slice(0, 6).join(':'), offset: 0, length: 6 },
        'Source:': { value: eth_hdr.slice(6, 12).join(':'), offset: 6, length: 6 },
        'Type/Length:': { value: eth_type_length_string, offset: 12, length: 2 },
    };
}

function decode_llc_header (llc_hdr) {

	let dsap = llc_hdr.slice(0,1).join("");
	let ssap = llc_hdr.slice(1,2).join("");
	let dsap_string = "";
	let ssap_string = "";

	if (dsap === "42") {
		dsap_string = "Spaning Tree BPDU (0x42)";
	}

	if (ssap === "42") {
		ssap_string = "Spanning Tree BPDU (0x42)";
	}

    return {
        'DSAP:': { value: dsap_string, offset: 0, length: 1 },
        'SSAP:': { value: ssap_string, offset: 1, length: 1 },
        'Control field:': { value: llc_hdr.slice(2, 3).join(''), offset: 2, length: 1 },
    };
}

function decode_stp_header (stp_hdr) {

	let protocol_id = stp_hdr.slice(0,2).join("");
	let bpdu_type = stp_hdr.slice(3,4).join("");
	let bpdu_flags = stp_hdr.slice(4,5).join("");
	let protocol_id_string = "";
	let bpdu_type_string = "";
	let bpdu_flags_string = "";
	let root_identifier_string = "";
	let bridge_identifier_string = "";

	if (protocol_id === "0000") {
		protocol_id_string = "Spanning Tree Protocol (0x000)";
	}

	if (bpdu_type === "00") {
		bpdu_type_string = "Configuration (0x00)";
	}

	if (bpdu_flags === "00") {
		bpdu_flags_string = "0x00";
	} else if (bpdu_flags === "01") {	
		bpdu_flags_string = "0x01, Topology Change";
	}

	root_identifier_string = parseInt(stp_hdr.slice(5,6).join(""), 16).toString();
	root_identifier_string = root_identifier_string + " / " + parseInt(stp_hdr.slice(6,7).join(""), 16).toString();
	root_identifier_string = root_identifier_string + " / " + stp_hdr.slice(7,13).join(":");

	bridge_identifier_string = parseInt(stp_hdr.slice(17,18).join(""), 16).toString();
	bridge_identifier_string = bridge_identifier_string + " / " + parseInt(stp_hdr.slice(18,19).join(""), 16).toString();
	bridge_identifier_string = bridge_identifier_string + " / " + stp_hdr.slice(19,25).join(":");

    return {
        'Protocol Identifier:': { value: protocol_id_string, offset: 0, length: 2 },
        'Protocol Version Identifier:': { value: `Spanning Tree (${parseInt(stp_hdr.slice(2, 3).join(''), 16).toString()})`, offset: 2, length: 1 },
        'BPDU Type:': { value: bpdu_type_string, offset: 3, length: 1 },
        'BPDU flags:': { value: bpdu_flags_string, offset: 4, length: 1 },
        'Root Identifier:': { value: root_identifier_string, offset: 5, length: 8 },
        'Root Path Cost:': { value: parseInt(stp_hdr.slice(13, 17).join(''), 16).toString(), offset: 13, length: 4 },
        'Bridge Identifier:': { value: bridge_identifier_string, offset: 17, length: 8 },
        'Port identifier:': { value: `0x${stp_hdr.slice(25, 27).join('')}`, offset: 25, length: 2 },
        'Message Age:': { value: (parseInt(stp_hdr.slice(27, 29).join(''), 16) / 256).toString(), offset: 27, length: 2 },
        'Max Age:': { value: (parseInt(stp_hdr.slice(29, 31).join(''), 16) / 256).toString(), offset: 29, length: 2 },
        'Hello Time:': { value: (parseInt(stp_hdr.slice(31, 33).join(''), 16) / 256).toString(), offset: 31, length: 2 },
        'Forward Delay:': { value: (parseInt(stp_hdr.slice(33, 35).join(''), 16) / 256).toString(), offset: 33, length: 2 },
    };
}

function decode_arp_header (arp_hdr) {

	let hw_type = arp_hdr.slice(0,2).join("");
	let hw_type_string = "";
	let proto_type = arp_hdr.slice(2,4).join("");
	let proto_type_string = "";
	let opcode = arp_hdr.slice(6,8).join("");
	let opcode_string = "";

	if (arp_hdr.length < 28) {
		console.log("Mimishark: arp headr is too short");
		return {};
	}

	if (hw_type === "0001") {
		hw_type_string = "Ethernet (00 01)";
	}

	if (proto_type === "0800") {
		proto_type_string = "IPv4 (08 00)";
	}

	if (opcode === "0001") {
		opcode_string = "request (00 01)";
	} else if (opcode === "0002") {
		opcode_string = "reply (00 02)";
	}


    return {
        'Hardware type:': { value: hw_type_string, offset: 0, length: 2 },
        'Protocol type:': { value: proto_type_string, offset: 2, length: 2 },
        'Hardware size:': { value: arp_hdr.slice(4, 5).toString(), offset: 4, length: 1 },
        'Protocol size:': { value: arp_hdr.slice(5, 6).toString(), offset: 5, length: 1 },
        'Opcode:': { value: opcode_string, offset: 6, length: 2 },
        'Sender MAC address:': { value: arp_hdr.slice(8, 14).join(':'), offset: 8, length: 6 },
        'Sender IP address:': { value: hex_to_ip(arp_hdr.slice(14, 18)), offset: 14, length: 4 },
        'Target MAC address:': { value: arp_hdr.slice(18, 24).join(':'), offset: 18, length: 6 },
        'Target IP address:': { value: hex_to_ip(arp_hdr.slice(24, 28)), offset: 24, length: 4 },
    };
}

function decode_ip_header (ip_hdr) {

	let ip_ver = ip_hdr.slice(0,1).toString().split("")[0];
	let ip_hdr_len = ip_hdr.slice(0,1).toString().split("")[1];
	let ip_ver_string = "";
	let ip_hdr_len_string = "";
	let ip_protocol = ip_hdr.slice(9,10).join("");
	let ip_protocol_string = "";
	let ip_flag_and_offset = parseInt(ip_hdr.slice(6, 8).join(""), 16);

	if (ip_hdr.length < 20) {
		console.log("Mimishark: ip header is too small");
		return {};
	}

	if (ip_ver === "4") {
		ip_ver_string = "Version: 4";
	}

	if (ip_hdr_len === "5") {
		ip_hdr_len_string = "Header Length: 20 bytes (5)";
	}

	if (ip_protocol === "01") {
		ip_protocol_string = "ICMP (01)";
	} else if (ip_protocol === "06") {
		ip_protocol_string = "TCP (06)";
	} else if (ip_protocol === "11") {
		ip_protocol_string = "UDP (17)";
	} else if (ip_protocol === "04") {	
		ip_protocol_string = "IPv4 encapsulation (04)";
	} else if (ip_protocol === "2f") {
		ip_protocol_string = "GRE (47)";
	} else {
		ip_protocol_string = "Uknown protocol";
	}
	
    return {
        'xxxx .... = ': { value: ip_ver_string, offset: 0, length: 1 },
        '.... xxxx = ': { value: ip_hdr_len_string, offset: 0, length: 1 },
        'Differentiated Service Field:': { value: ip_hdr.slice(1, 2).toString(), offset: 1, length: 1 },
        'Total Length:': { value: parseInt(ip_hdr.slice(2, 4).join(''), 16).toString(), offset: 2, length: 2 },
        'Identification:': { value: `0x${ip_hdr.slice(4, 6).join('')}`, offset: 4, length: 2 },
        'Flag and Fragment Offset:': { value: ip_hdr.slice(6, 8).join(''), offset: 6, length: 2 },
        '...x xxxx xxxx xxxx = Fragment Offset:': { value: (ip_flag_and_offset & 8191) * 8, offset: 6, length: 2 },
        'Time to Live:': { value: parseInt(ip_hdr.slice(8, 9).join(''), 16).toString(), offset: 8, length: 1 },
        'Protocol:': { value: ip_protocol_string, offset: 9, length: 1 },
        'Header Checksum:': { value: `0x${ip_hdr.slice(10, 12).join('')}`, offset: 10, length: 2 },
        'Source Address:': { value: hex_to_ip(ip_hdr.slice(12, 16)), offset: 12, length: 4 },
        'Destination Address:': { value: hex_to_ip(ip_hdr.slice(16, 20)), offset: 16, length: 4 },
    };
}

function decode_icmp_header(icmp_hdr) {
    if (icmp_hdr.length < 8) {
        console.log('Mimishark: ICMP header is too small');
        return {};
    }

    const icmp_type = icmp_hdr.slice(0, 1).join('');
    let icmp_type_string = '';

    if (icmp_type === '08') {
        icmp_type_string = '8 (Echo (ping) request)';
        return {
            'Type:': { value: icmp_type_string, offset: 0, length: 1 },
            'Code:': { value: icmp_hdr.slice(1, 2).join(''), offset: 1, length: 1 },
            'Checksum:': { value: `0x${icmp_hdr.slice(2, 4).join('')}`, offset: 2, length: 2 },
            'Identifier:': { value: `0x${icmp_hdr.slice(4, 6).join('')}`, offset: 4, length: 2 },
            'Sequence Number:': { value: `0x${icmp_hdr.slice(6, 8).join('')}`, offset: 6, length: 2 },
        };
    } else if (icmp_type === '00') {
        icmp_type_string = '0 (Echo (ping) reply)';
        return {
            'Type:': { value: icmp_type_string, offset: 0, length: 1 },
            'Code:': { value: icmp_hdr.slice(1, 2).join(''), offset: 1, length: 1 },
            'Checksum:': { value: `0x${icmp_hdr.slice(2, 4).join('')}`, offset: 2, length: 2 },
            'Identifier:': { value: `0x${icmp_hdr.slice(4, 6).join('')}`, offset: 4, length: 2 },
            'Sequence Number:': { value: `0x${icmp_hdr.slice(6, 8).join('')}`, offset: 6, length: 2 },
        };
    } else if (icmp_type === '03') {
        const icmp_code = icmp_hdr.slice(1, 2).join('');
        let icmp_code_string = '';
        icmp_type_string = '3 (Destination unreachable)';

        if (icmp_code === '00') icmp_code_string = '0 (Network unreachable)';
        else if (icmp_code === '01') icmp_code_string = '1 (Host unreachable)';
        else if (icmp_code === '03') icmp_code_string = '3 (Port unreachable)';
        else if (icmp_code === '04') icmp_code_string = '4 (Fragmentation needed and DF set)';

        return {
            'Type:': { value: icmp_type_string, offset: 0, length: 1 },
            'Code:': { value: icmp_code_string, offset: 1, length: 1 },
            'Checksum:': { value: `0x${icmp_hdr.slice(2, 4).join('')}`, offset: 2, length: 2 },
            'Unused:': { value: icmp_hdr.slice(4, 8).join(''), offset: 4, length: 4 },
        };
    } else if (icmp_type === '05') {
        const icmp_code = icmp_hdr.slice(1, 2).join('');
        let icmp_code_string = '';

        if (icmp_code === '00') icmp_code_string = '0 (Redirect for the Network)';
        else if (icmp_code === '01') icmp_code_string = '1 (Redirect for the Host)';
        else if (icmp_code === '02') icmp_code_string = '2 (Redirect for the Type of Service and Network)';
        else if (icmp_code === '03') icmp_code_string = '3 (Redirect for the Type of Service and Host)';

        icmp_type_string = '5 (Redirect Message)';

        return {
            'Type:': { value: icmp_type_string, offset: 0, length: 1 },
            'Code:': { value: icmp_code_string, offset: 1, length: 1 },
            'Checksum:': { value: `0x${icmp_hdr.slice(2, 4).join('')}`, offset: 2, length: 2 },
            'Gateway:': { value: hex_to_ip(icmp_hdr.slice(4, 8)), offset: 4, length: 4 },
        };
    } else if (icmp_type === '0b') {
        const icmp_code = icmp_hdr.slice(1, 2).join('');
        let icmp_code_string = '';

        if (icmp_code === '00') icmp_code_string = '0 (Time To Live exceeded in transit)';
        else if (icmp_code === '01') icmp_code_string = '1 (Fragment reassembly time exceeded)';

        icmp_type_string = '11 (Time To Live Exceeded)';

        return {
            'Type:': { value: icmp_type_string, offset: 0, length: 1 },
            'Code:': { value: icmp_code_string, offset: 1, length: 1 },
            'Checksum:': { value: `0x${icmp_hdr.slice(2, 4).join('')}`, offset: 2, length: 2 },
            'Unused:': { value: icmp_hdr.slice(4, 8).join(''), offset: 4, length: 4 },
        };
    }

    return {};
}

function decode_udp_header (udp_hdr) {

	if (udp_hdr.length < 8) {
		console.log("Mimishark: UDP header is too small");
		return {};
	}

	return {
        'Source Port:': { value: parseInt(udp_hdr.slice(0, 2).join(''), 16).toString(), offset: 0, length: 2 },
        'Destination Port:': { value: parseInt(udp_hdr.slice(2, 4).join(''), 16).toString(), offset: 2, length: 2 },
        'Length:': { value: parseInt(udp_hdr.slice(4, 6).join(''), 16).toString(), offset: 4, length: 2 },
        'Checksum:': { value: `0x${udp_hdr.slice(6, 8).join('')}`, offset: 6, length: 2 },
    };
}

function decode_tcp_header (tcp_hdr) {

	let tcp_hdr_len = parseInt(tcp_hdr.slice(12, 13).join(""), 16) >> 4;

	if (tcp_hdr.length < 20) {
		console.log("Mimishark: TCP header is too small");
		return {};
	}


	return {
        'Source Port:': { value: parseInt(tcp_hdr.slice(0, 2).join(''), 16).toString(), offset: 0, length: 2 },
        'Destination Port:': { value: parseInt(tcp_hdr.slice(2, 4).join(''), 16).toString(), offset: 2, length: 2 },
        'Sequence Number:': { value: parseInt(tcp_hdr.slice(4, 8).join(''), 16).toString(), offset: 4, length: 4 },
        'Acknowledge Number:': { value: parseInt(tcp_hdr.slice(8, 12).join(''), 16).toString(), offset: 8, length: 4 },
        'xxxx .... = Header Length: ': { value: `${tcp_hdr_len * 4} bytes (${tcp_hdr_len})`, offset: 12, length: 1 },
        'Flags:': { value: `0x${tcp_hdr.slice(13, 14).join('')}`, offset: 13, length: 1 },
        'Window:': { value: parseInt(tcp_hdr.slice(14, 16).join(''), 16).toString(), offset: 14, length: 2 },
        'Checksum:': { value: `0x${tcp_hdr.slice(16, 18).join('')}`, offset: 16, length: 2 },
        'Urgent Pointer:': { value: `0x${tcp_hdr.slice(18, 20).join('')}`, offset: 18, length: 2 },
    };
}

function decode_gre_header (gre_hdr) {

	// By default
	let gre_hdr_length = 4;

	if (gre_hdr.length < gre_hdr_length) {
		console.log("Mimishark: GRE header is too small");
		return {};
	}

	let flags_and_version = gre_hdr.slice(0,2);
	const C = flags_and_version & 32768;
	const R = flags_and_version & 16384;
	const K = flags_and_version & 8192;
	const S = flags_and_version & 4096;
	const s = flags_and_version & 2048;
	const Recur = flags_and_version & 1792;
	const Flags = flags_and_version & 240;
	const Version = flags_and_version & 15;

	const ProtocolType = gre_hdr.slice(2,4).join("");

	let protocol_type_string = "";

	if (ProtocolType === "0800") {
		protocol_type_string = "IPv4 (0x0800)";
	} else {
		protocol_type_string = "Unknown protocol";
	}


	const ret_val = {
        'x... .... .... .... = checksum bit: ': { value: Boolean(C).toString(), offset: 0, length: 2 },
        '.X.. .... .... .... = routing bit: ': { value: Boolean(R).toString(), offset: 0, length: 2 },
        '..X. .... .... .... = key bit: ': { value: Boolean(K).toString(), offset: 0, length: 2 },
        '...X .... .... .... = sequence number bit: ': { value: Boolean(S).toString(), offset: 0, length: 2 },
        '.... X... .... .... = strict source route bit: ': { value: Boolean(s).toString(), offset: 0, length: 2 },
        '.... .XXX .... .... = recursion control: ': { value: Recur.toString(), offset: 0, length: 2 },
        '.... .... XXXX X... = flags: ': { value: Flags.toString(), offset: 0, length: 2 },
        '.... .... .... .XXX = version: ': { value: Version.toString(), offset: 0, length: 2 },
        'Protocol type: ': { value: protocol_type_string, offset: 2, length: 2 },
    };

	// Optional fields extend the header length; callers use GRE_header_length to slice payload.
    if (C) {
        ret_val['Checksum'] = { value: parseInt(gre_hdr.slice(4, 6).join(''), 16).toString(), offset: 4, length: 2 };
        ret_val['Offset'] = { value: parseInt(gre_hdr.slice(6, 8).join(''), 16).toString(), offset: 6, length: 2 };
        gre_hdr_length += 8;
    }

    if (K) {
        ret_val['Key'] = { value: parseInt(gre_hdr.slice(8, 12).join(''), 16).toString(), offset: 8, length: 4 };
        gre_hdr_length += 4;
    }

    if (S) {
        ret_val['Sequence number'] = { value: parseInt(gre_hdr.slice(12, 16).join(''), 16).toString(), offset: 12, length: 4 };
        gre_hdr_length += 4;
    }

    ret_val['GRE_header_length'] = { value: gre_hdr_length, offset: 0, length: gre_hdr_length };
    return ret_val;
}

function add_llc_header (pkt, header_number) {

	make_pa("Logical-Link Control", header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;

	pkt_decode = decode_llc_header(pkt);

	for (var k in pkt_decode) {
		let decode_p = document.createElement("p");
		decode_p.innerHTML = `${k} ${pkt_decode[k].value}`;
		decode_div.appendChild(decode_p);
	}

	decode.appendChild(decode_div);
}

function add_stp_header (pkt, header_number) {

	make_pa("Spanning Tree Protocol", header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;

	pkt_decode = decode_stp_header(pkt);

	for (var k in pkt_decode) {
		let decode_p = document.createElement("p");
		decode_p.innerHTML = `${k} ${pkt_decode[k].value}`;
		decode_div.appendChild(decode_p);
	}

	decode.appendChild(decode_div);
}

function add_arp_header(pkt, header_number) {

	make_pa("Address Resolution Protocol", header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;

	pkt_decode = decode_arp_header(pkt);

	for (var k in pkt_decode) {
		let decode_p = document.createElement("p");
		decode_p.innerHTML = `${k} ${pkt_decode[k].value}`;
		decode_div.appendChild(decode_p);
	}
	
	decode.appendChild(decode_div);
}

function add_ipv4_header (pkt, header_number) {

	make_pa("Internet Protocol Version 4", header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;
	pkt_decode = decode_ip_header(pkt);

	for (var k in pkt_decode) {
		let decode_p = document.createElement("p");
		decode_p.innerHTML = `${k} ${pkt_decode[k].value}`;
		decode_div.appendChild(decode_p);
	}

	decode.appendChild(decode_div);
}

function add_icmp_header (pkt, header_number) {

	make_pa("Internet Control Message Protocol", header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;

	pkt_decode = decode_icmp_header(pkt);

	for (var k in pkt_decode) {
		let decode_p = document.createElement("p");
		decode_p.innerHTML = `${k} ${pkt_decode[k].value}`;
		decode_div.appendChild(decode_p);
	}

    const tcp_hdr_len = (parseInt(pkt.slice(12, 13).join(''), 16) >> 4) * 4;
    const payload_bytes = pkt.length - tcp_hdr_len - 8;
    if (payload_bytes > 0) {
        const payload_p = document.createElement('p');
        payload_p.innerHTML = `Data: ${payload_bytes} bytes`;
        decode_div.appendChild(payload_p);
    }

	decode.appendChild(decode_div);
}

function add_tcp_header (pkt, header_number) {

	make_pa("Transmission Control Protocol", header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;

	pkt_decode = decode_tcp_header(pkt);

	for (var k in pkt_decode) {
		let decode_p = document.createElement("p");
		decode_p.innerHTML = `${k} ${pkt_decode[k].value}`;
		decode_div.appendChild(decode_p);
	}

    const tcp_hdr_len = (parseInt(pkt.slice(12, 13).join(''), 16) >> 4) * 4;
    const payload_bytes = pkt.length - tcp_hdr_len;
    if (payload_bytes > 0) {
        const payload_p = document.createElement('p');
        payload_p.innerHTML = `Data: ${payload_bytes} bytes`;
        decode_div.appendChild(payload_p);
    }

	decode.appendChild(decode_div);
}

function add_udp_header (pkt, header_number) {

	make_pa("User Datagram Protocol", header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;

	pkt_decode = decode_udp_header(pkt);

	for (var k in pkt_decode) {
		let decode_p = document.createElement("p");
		decode_p.innerHTML = `${k} ${pkt_decode[k].value}`;
		decode_div.appendChild(decode_p);
	}

    const payload_bytes = pkt.length - 8;
    if (payload_bytes > 0) {
        const payload_p = document.createElement('p');
        payload_p.innerHTML = `Data: ${payload_bytes} bytes`;
        decode_div.appendChild(payload_p);
    }

	decode.appendChild(decode_div);
}

function add_gre_header (pkt, header_number) {

	make_pa("Generic routing encapsulation (GRE)", header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;

	pkt_decode = decode_gre_header(pkt);

	let gre_hdr_len = 8;

	for (var k in pkt_decode) {

		if (k === "GRE_header_length") {
			gre_hdr_len = pkt_decode[k];
			continue;
		}

		let decode_p = document.createElement("p");
		decode_p.innerHTML = k + " " + pkt_decode[k];
		decode_div.appendChild(decode_p);
	}

    const payload_bytes = pkt.length - gre_hdr_len;
    if (payload_bytes > 0) {
        const payload_p = document.createElement('p');
        payload_p.innerHTML = `Data: ${payload_bytes} bytes`;
        decode_div.appendChild(payload_p);
    }

	decode.appendChild(decode_div);

	return gre_hdr_len;
}

function decode_packet(pkt) {
	
	pkt = pkt.split(/ /);
	let header_number = 5;
	let current_offset = 0;

	// Check if packet is long enought
	if (pkt.length < 14){
		console.log("Mimishark: packet is too short");
		return 1;
	}

	make_pa("Ethernet Frame", header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;

	pkt_decode = decode_ethernet_header(pkt.slice(0, pkt.length));

	for (const [label, field] of Object.entries(pkt_decode)) {
        const decode_p = document.createElement('p');
        decode_p.innerHTML = `${label} ${field.value}`;
        decode_div.appendChild(decode_p);
    }

	decode.appendChild(decode_div);
	header_number = header_number + 1;
    current_offset += 14;

	let eth_type = pkt.slice(12,14).join("");
	let next_header = eth_type;

	// Drop Ethernet header.
	pkt = pkt.slice(14);

	// LLC
	if (parseInt(next_header, 16) < 1500) {
		add_llc_header(pkt, header_number);
		header_number = header_number + 1;

		let dsap = pkt.slice(0,1).join("");

		// STP
		if (dsap === "42"){
			add_stp_header(pkt.slice(3), header_number);
		}

		return 0;

	// ARP
	} else if (next_header === "0806") {
		add_arp_header(pkt, header_number);
		return 0;
	} 

	while (true) {

		// IPv4 or IP tunnel
		if (next_header === "0800" || next_header === "04") {
			add_ipv4_header(pkt, header_number);
			header_number = header_number + 1;
			
			let ip_protocol = pkt.slice(9,10).join("");
			let ip_hdr_len = parseInt(pkt.slice(0,1).toString().split("")[1], 16) * 4;
			let ip_offset = parseInt(pkt.slice(6, 8).join(""), 16) & 8191;

			// Don't parse if IP offset not 0.
			if (ip_offset) {
				return 0;
			}

			// Drop IP header
			pkt = pkt.slice(ip_hdr_len);

			// ICMP
			if (ip_protocol === "01") {
				add_icmp_header(pkt, header_number);
				header_number = header_number + 1;
				break;
			
			// TCP
			} else if (ip_protocol === "06") {
				add_tcp_header(pkt, header_number);
				header_number = header_number + 1;
				break;
			
			// UDP
			} else if (ip_protocol === "11") {
				add_udp_header(pkt, header_number);
				header_number = header_number + 1;
				break;
			
			// IP
			} else if (ip_protocol === "04") {
				next_header = ip_protocol;
				continue;

			// GRE
			} else if (ip_protocol === "2f") {
				let h_len = add_gre_header(pkt, header_number);
				header_number = header_number + 1;

				// Who is next?
				next_header = pkt.slice(2,4).join("");
				pkt = pkt.slice(h_len);
				continue;

			// Unknown protocol
			} else {
				break;
			}
		} else {
			break;
		}
	}
	
	return 0;
}

function parse_packet_structure(pkt) {
    const bytes = pkt.split(/ /);
    const headers = [];
    let offset = 0;

    if (bytes.length < 14) {
        console.log('Mimishark: packet is too short');
        return headers;
    }

    // Ethernet
    const eth_hdr = bytes.slice(0, 14);
    const eth_decode = decode_ethernet_header(eth_hdr);
    headers.push({
        className: 'Ethernet Frame',
        startByte: offset,
        byteCount: 14,
        fields: Object.entries(eth_decode).map(([label, field]) => ({
            label,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(label),
            startByte: offset + field.offset
        }))
    });
    offset += 14;

    const eth_type = bytes.slice(12, 14).join('');
    let remaining = bytes.slice(14);

    // LLC + STP
    if (parseInt(eth_type, 16) < 1500) {
        const llc_hdr = remaining.slice(0, 3);
        const llc_decode = decode_llc_header(llc_hdr);
        headers.push({
            className: 'Logical-Link Control',
            startByte: offset,
            byteCount: 3,
            fields: Object.entries(llc_decode).map(([label, field]) => ({
                label,
                value: field.value,
                offset: field.offset,
                len: field.length,
                className: toHoverKey(label),
                startByte: offset + field.offset
            }))
        });
        offset += 3;

        if (llc_hdr[0] === '42') {
            const stp_hdr = remaining.slice(3);
            const stp_decode = decode_stp_header(stp_hdr);
            headers.push({
                className: 'Spanning Tree Protocol',
                startByte: offset,
                byteCount: stp_hdr.length,
                fields: Object.entries(stp_decode).map(([label, field]) => ({
                    label,
                    value: field.value,
                    offset: field.offset,
                    len: field.length,
                    className: toHoverKey(label),
                    startByte: offset + field.offset
                }))
            });
        }
        return headers;
    }

    // ARP
    if (eth_type === '0806') {
        const arp_hdr = remaining.slice(0, 28);
        const arp_decode = decode_arp_header(arp_hdr);
        headers.push({
            className: 'Address Resolution Protocol',
            startByte: offset,
            byteCount: 28,
            fields: Object.entries(arp_decode).map(([label, field]) => ({
                label,
                value: field.value,
                offset: field.offset,
                len: field.length,
                className: toHoverKey(label),
                startByte: offset + field.offset
            }))
        });
        return headers;
    }

    // IPv4
    if (eth_type === '0800') {
        if (remaining.length < 20) {
            console.log('Mimishark: IPv4 header is too short');
            return headers;
        }

        const ihl = parseInt(remaining[0][1], 16);
        const ip_hdr_len = ihl * 4;
        const ip_hdr = remaining.slice(0, ip_hdr_len);
        const ip_decode = decode_ip_header(ip_hdr);
        headers.push({
            className: 'Internet Protocol Version 4',
            startByte: offset,
            byteCount: ip_hdr_len,
            fields: Object.entries(ip_decode).map(([label, field]) => ({
                label,
                value: field.value,
                offset: field.offset,
                len: field.length,
                className: toHoverKey(label),
                startByte: offset + field.offset
            }))
        });
        offset += ip_hdr_len;
        remaining = remaining.slice(ip_hdr_len);

        const protocol = ip_hdr[9];

        // TCP
        if (protocol === '06') {
            if (remaining.length < 20) return headers;

            const data_offset = parseInt(remaining[12], 16) >> 4;
            const tcp_hdr_len = data_offset * 4;
            const full_tcp = remaining.slice(0, tcp_hdr_len + (remaining.length > tcp_hdr_len ? remaining.length - tcp_hdr_len : 0));
            const tcp_hdr = remaining.slice(0, tcp_hdr_len);
            const tcp_decode = decode_tcp_header(tcp_hdr);

            const tcpHeader = {
                className: 'Transmission Control Protocol',
                startByte: offset,
                byteCount: full_tcp.length,
                fields: Object.entries(tcp_decode).map(([label, field]) => ({
                    label,
                    value: field.value,
                    offset: field.offset,
                    len: field.length,
                    className: toHoverKey(label),
                    startByte: offset + field.offset
                }))
            };

            if (remaining.length > tcp_hdr_len) {
                tcpHeader.fields.push({
                    label: 'Data',
                    value: '',
                    offset: tcp_hdr_len,
                    len: remaining.length - tcp_hdr_len,
                    className: toHoverKey('Data'),
                    startByte: offset + tcp_hdr_len
                });
            }

            headers.push(tcpHeader);
            return headers;
        }

        // ICMP
        if (protocol === '01') {
            if (remaining.length < 8) {
                console.log('Mimishark: ICMP header is too short');
                return headers;
            }

            const full_icmp = remaining;
            const icmp_hdr = remaining.slice(0, 8);
            const icmp_decode = decode_icmp_header(icmp_hdr);

            const icmpHeader = {
                className: 'Internet Control Message Protocol',
                startByte: offset,
                byteCount: full_icmp.length,
                fields: Object.entries(icmp_decode).map(([label, field]) => ({
                    label,
                    value: field.value,
                    offset: field.offset,
                    len: field.length,
                    className: toHoverKey(label),
                    startByte: offset + field.offset
                }))
            };

            if (full_icmp.length > 8) {
                icmpHeader.fields.push({
                    label: 'Data',
                    value: '',
                    offset: 8,
                    len: full_icmp.length - 8,
                    className: toHoverKey('Data'),
                    startByte: offset + 8
                });
            }

            headers.push(icmpHeader);
            return headers;
        }

        // UDP
        if (protocol === '11') {
            if (remaining.length < 8) return headers;

            const full_udp = remaining;
            const udp_hdr = remaining.slice(0, 8);
            const udp_decode = decode_udp_header(udp_hdr);

            const udpHeader = {
                className: 'User Datagram Protocol',
                startByte: offset,
                byteCount: full_udp.length,
                fields: Object.entries(udp_decode).map(([label, field]) => ({
                    label,
                    value: field.value,
                    offset: field.offset,
                    len: field.length,
                    className: toHoverKey(label),
                    startByte: offset + field.offset
                }))
            };

            if (remaining.length > 8) {
                udpHeader.fields.push({
                    label: 'Data',
                    value: '',
                    offset: 8,
                    len: remaining.length - 8,
                    className: toHoverKey('Data'),
                    startByte: offset + 8
                });
            }

            headers.push(udpHeader);
            return headers;
        }

        // GRE
        if (protocol === '2f') {
            if (remaining.length < 4) return headers;

            const gre_decode = decode_gre_header(remaining);
            const gre_hdr_len = gre_decode.GRE_header_length.value;
            const full_gre = remaining.slice(0, gre_hdr_len + (remaining.length > gre_hdr_len ? remaining.length - gre_hdr_len : 0));

            const greHeader = {
                className: 'Generic Routing Encapsulation',
                startByte: offset,
                byteCount: full_gre.length,
                fields: Object.entries(gre_decode)
                    .filter(([k]) => k !== 'GRE_header_length')
                    .map(([label, field]) => ({
                        label,
                        value: field.value,
                        offset: field.offset,
                        len: field.length,
                        className: toHoverKey(label),
                        startByte: offset + field.offset
                    }))
            };

            if (remaining.length > gre_hdr_len) {
                greHeader.fields.push({
                    label: 'Data',
                    value: '',
                    offset: gre_hdr_len,
                    len: remaining.length - gre_hdr_len,
                    className: toHoverKey('Data'),
                    startByte: offset + gre_hdr_len
                });
            }

            headers.push(greHeader);
            return headers;
        }
    }

    // Payload
    if (remaining.length > 0) {
        headers.push({
            className: 'Data',
            startByte: offset,
            byteCount: remaining.length,
            fields: []
        });
    }

    return headers;
}

function createByteDivs(pkt, pktData) {
    const rowsEl = document.querySelector('#rows');
    const inputEl = document.querySelector('#bytes');
    const asciiEl = document.querySelector('#ascii');

    rowsEl.replaceChildren();
    inputEl.replaceChildren();
    asciiEl.replaceChildren();

    const decoded = parse_packet_structure(pkt);
    const bytes = pkt.split(/ /);
    const string = pktData['bytes'];
    const asciiString = pktData['ascii'].replace(/doublePrime/g, '"').replace(/singlePrime/g, "'");

    const totalLines = Math.ceil(string.length / 47);

    for (let line = 0; line < totalLines; line++) {
        const byteP = document.createElement('p');
        const byteDivs = [];
        const processedBytes = new Set();

        const lineStartHex = line * 47 + line;
        const lineEndHex = Math.min(lineStartHex + 47, string.length);
        const lineHex = string.substring(lineStartHex, lineEndHex).trim();

        const lineStartByte = line * 16;
        const lineEndByte = Math.min(lineStartByte + 16, bytes.length);

        decoded.forEach(header => {
            const hStart = header.startByte;
            const hEnd = hStart + header.byteCount;

            if (hStart >= lineEndByte || hEnd <= lineStartByte) return;

            const headerDiv = document.createElement('div');
            headerDiv.className = toHoverKey(header.className);
            headerDiv.dataset.startByte = hStart;
            headerDiv.dataset.byteCount = header.byteCount;
            headerDiv.style.display = 'inline';

            if (header.fields.length > 0) {
                header.fields.forEach((field, i) => {
                    const fStart = field.startByte;
                    const fEnd = fStart + field.len;

                    if (fStart >= lineEndByte || fEnd <= lineStartByte) return;

                    const fieldDiv = document.createElement('div');
                    fieldDiv.className = toHoverKey(field.label, header.className);
                    fieldDiv.dataset.startByte = fStart;
                    fieldDiv.dataset.byteCount = field.len;
                    fieldDiv.style.display = 'inline';

                    for (let i = Math.max(fStart, lineStartByte); i < Math.min(fEnd, lineEndByte); i++) {
                        if (processedBytes.has(i)) continue;

                        const span = document.createElement('span');
                        span.className = 'byte';
                        span.dataset.byteIndex = i;
                        span.textContent = bytes[i];
                        fieldDiv.appendChild(span);
                        processedBytes.add(i);

                        if (i < Math.min(fEnd - 1, lineEndByte - 1)) {
                            const space = document.createElement('span');
                            space.className = 'byte-space';
                            space.textContent = ' ';
                            fieldDiv.appendChild(space);
                        }
                    }

                    if (fieldDiv.children.length > 0) {
                        headerDiv.appendChild(fieldDiv);
                        if (i < header.fields.length - 1) {
                            headerDiv.appendChild(document.createTextNode(' '));
                        }
                    }
                });
            } else {
                for (let i = Math.max(hStart, lineStartByte); i < Math.min(hEnd, lineEndByte); i++) {
                    if (processedBytes.has(i)) continue;

                    const span = document.createElement('span');
                    span.className = 'byte';
                    span.dataset.byteIndex = i;
                    span.textContent = bytes[i];
                    headerDiv.appendChild(span);
                    processedBytes.add(i);

                    if (i < Math.min(hEnd - 1, lineEndByte - 1)) {
                        const space = document.createElement('span');
                        space.className = 'byte-space';
                        space.textContent = ' ';
                        headerDiv.appendChild(space);
                    }
                }
            }

            if (headerDiv.children.length > 0) {
                byteDivs.push(headerDiv);
            }
        });

        byteDivs.sort((a, b) => +a.dataset.startByte - +b.dataset.startByte);
        byteDivs.forEach((div, i) => {
            byteP.appendChild(div);
            if (i < byteDivs.length - 1) {
                const next = byteDivs[i + 1];
                if (+div.dataset.startByte + +div.dataset.byteCount === +next.dataset.startByte) {
                    byteP.appendChild(document.createTextNode(' '));
                }
            }
        });

        if (byteDivs.length > 0) {
            inputEl.appendChild(byteP);

            const rowP = document.createElement('p');
            rowP.textContent = line.toString().padStart(4, '0');
            rowsEl.appendChild(rowP);
        }

        const asciiP = document.createElement('p');
        asciiP.style.whiteSpace = 'nowrap';
        const asciiDivs = [];
        const processedAscii = new Set();

        decoded.forEach(header => {
            const hStart = header.startByte;
            const hEnd = hStart + header.byteCount;

            if (hStart >= lineEndByte || hEnd <= lineStartByte) return;

            const headerDiv = document.createElement('div');
            headerDiv.className = toHoverKey(header.className);
            headerDiv.dataset.startByte = hStart;
            headerDiv.dataset.byteCount = header.byteCount;
            headerDiv.style.display = 'inline';

            if (header.fields.length > 0) {
                header.fields.forEach(field => {
                    const fStart = field.startByte;
                    const fEnd = fStart + field.len;

                    if (fStart >= lineEndByte || fEnd <= lineStartByte) return;

                    const fieldDiv = document.createElement('div');
                    fieldDiv.className = toHoverKey(field.label, header.className);
                    fieldDiv.dataset.startByte = fStart;
                    fieldDiv.dataset.byteCount = field.len;
                    fieldDiv.style.display = 'inline';

                    for (let i = Math.max(fStart, lineStartByte); i < Math.min(fEnd, lineEndByte); i++) {
                        if (processedAscii.has(i)) continue;

                        const span = document.createElement('span');
                        span.className = 'ascii-char';
                        span.dataset.byteIndex = i;
                        span.textContent = asciiString[i] || '.';
                        fieldDiv.appendChild(span);
                        processedAscii.add(i);
                    }

                    if (fieldDiv.children.length > 0) {
                        headerDiv.appendChild(fieldDiv);
                    }
                });
            } else {
                for (let i = Math.max(hStart, lineStartByte); i < Math.min(hEnd, lineEndByte); i++) {
                    if (processedAscii.has(i)) continue;

                    const span = document.createElement('span');
                    span.className = 'ascii-char';
                    span.dataset.byteIndex = i;
                    span.textContent = asciiString[i] || '.';
                    headerDiv.appendChild(span);
                    processedAscii.add(i);
                }
            }

            if (headerDiv.children.length > 0) {
                asciiDivs.push(headerDiv);
            }
        });

        asciiDivs.sort((a, b) => +a.dataset.startByte - +b.dataset.startByte);
        asciiDivs.forEach(div => asciiP.appendChild(div));

        if (asciiDivs.length > 0) {
            asciiEl.appendChild(asciiP);
        }
    }
}

function enableHoverByHoverInfo() {
    const hoverInfo = document.querySelector('#decode')?.getAttribute('hoverInfo');
    if (!hoverInfo) return;

    document.querySelectorAll('.highlight').forEach(el => el.classList.remove('highlight'));

    const escaped = CSS.escape(hoverInfo);
    const selector = `#bytes .${escaped}, #bytes .${escaped} .byte, #bytes .${escaped} .byte-space, ` +
                     `#ascii .${escaped}, #ascii .${escaped} .ascii-char`;

    document.querySelectorAll(selector).forEach(el => {
        el.classList.add('highlight');
    });
}

function AddHoverInfoAttribute() {
    const decodeEl = document.querySelector('#decode');
    if (!decodeEl) return;

    decodeEl.querySelectorAll('.decode_head').forEach(head => {
        head.onclick = () => {
            const title = head.textContent.trim();
            const hoverKey = toHoverKey(title);
            decodeEl.setAttribute('hoverInfo', hoverKey);
            enableHoverByHoverInfo();
        };
    });

    decodeEl.querySelectorAll('.decode_body p').forEach(p => {
        p.onclick = () => {
            const text = p.textContent.trim();
            const parentCollapse = p.closest('.decode_body');
            const headerLink = parentCollapse?.previousElementSibling?.querySelector('a.decode_head');
            const protocolName = headerLink?.textContent.trim() || '';

            const hoverKey = toHoverKey(text, protocolName);
            decodeEl.setAttribute('hoverInfo', hoverKey);
            enableHoverByHoverInfo();
        };
    });
}

function toHoverKey(fieldText, protocolName) {
    const match = fieldText.match(/^([^:=]+)[:=]?/);
    const field = match ? match[1].trim() : fieldText.trim();

    const cleanField = field.replace(/\s+/g, '_');
    const cleanProtocol = protocolName ? protocolName.replace(/\s+/g, '_') : '';

    if (!cleanProtocol) return CSS.escape(cleanField);

    return CSS.escape(`${cleanProtocol}__${cleanField}`);
}
