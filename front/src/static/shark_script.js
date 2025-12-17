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
        this.classList.add('no-hover');
        this.classList.toggle('selected');

        createByteDivs(pcap_data[this.id - 1].bytes, pcap_data[this.id - 1]);
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
    decode_a.setAttribute('data-header-number', count);
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

function decode_vlan_header(vlan_bytes) {
    const type_hex = vlan_bytes.slice(2, 4).join('');
    const type_str = decode_ethertype(type_hex);
    const tci  = vlan_bytes.slice(0, 2).join('');
    const tci_num = parseInt(tci, 16);

    const pcp = (tci_num >> 13) & 0x7;
    const dei = (tci_num >> 12) & 0x1;
    const vid = tci_num & 0xfff;

    // Priority names
    const pcp_names = [
        'Best Effort (default) (0)',
        'Background (1)',
        'Excellent Effort (2)',
        'Critical Applications (3)',
        'Video, < 100 ms latency (4)',
        'Voice, < 10 ms latency (5)',
        'Internetwork Control (6)',
        'Network Control (7)'
    ];

    return {
        'Priority Code Point (PCP):': { 
            value: `${pcp_names[pcp]}`, 
            offset: 0, 
            length: 2 
        },
        'Drop Eligible Indicator (DEI):': { 
            value: dei === 0 ? 'Ineligible' : 'Eligible', 
            offset: 0, 
            length: 2,
        },
        // VID=0 → Priority Tag (no VLAN, PCP/DEI only)
        // The user is not expected to enter VLAN ID = 0.
        'VLAN Identifier (VID):': { 
            value: vid === 0 ? '0 (Priority tag)' : vid.toString(), 
            offset: 0, 
            length: 2 
        },
        'Type:': { 
            value: type_str, 
            offset: 2, 
            length: 2 
        },
    };
}

function decode_ethernet_header (eth_hdr) {
	let eth_type = eth_hdr.slice(12,14).join("");
	let eth_type_length_string;
	if (eth_hdr.length < 14) {
		console.log("Mimishark: Ethernet header is too short");
		return {};
	}
	// Do we have LLC packet
	if (parseInt(eth_type, 16) < 1500) {
		eth_type_length_string = parseInt(eth_type, 16).toString() + " bytes";
    } else {
        eth_type_length_string = decode_ethertype(eth_type);
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

function decode_tcp_header(tcp_hdr) {
    if (tcp_hdr.length < 20) {
        console.log("Mimishark: TCP header is too small");
        return {};
    }

    const dataOffsetByte = parseInt(tcp_hdr[12], 16);
    const dataOffset = (dataOffsetByte >> 4) & 0x0F;
    const tcp_hdr_len = dataOffset * 4;
    const options_len = Math.max(tcp_hdr_len - 20, 0);

    const result = {
        'Source Port:': { value: parseInt(tcp_hdr.slice(0, 2).join(''), 16).toString(), offset: 0, length: 2 },
        'Destination Port:': { value: parseInt(tcp_hdr.slice(2, 4).join(''), 16).toString(), offset: 2, length: 2 },
        'Sequence Number:': { value: `0x${tcp_hdr.slice(4, 8).join('')}`, offset: 4, length: 4 },
        'Acknowledge Number:': { value: `0x${tcp_hdr.slice(8, 12).join('')}`, offset: 8, length: 4 },
        'Data Offset:': { value: `${tcp_hdr_len} bytes (${dataOffset})`, offset: 12, length: 1 },
        'Flags:': { value: `0x${tcp_hdr.slice(13, 14).join('')}`, offset: 13, length: 1 },
        'Window:': { value: parseInt(tcp_hdr.slice(14, 16).join(''), 16).toString(), offset: 14, length: 2 },
        'Checksum:': { value: `0x${tcp_hdr.slice(16, 18).join('')}`, offset: 16, length: 2 },
        'Urgent Pointer:': { value: `0x${tcp_hdr.slice(18, 20).join('')}`, offset: 18, length: 2 },
    };

    if (options_len > 0) {
        result['TCP Options:'] = { 
            value: `${options_len} bytes`, 
            offset: 20, 
            length: options_len 
        };
    }

    const data_len = Math.max(tcp_hdr.length - tcp_hdr_len, 0);
    
    if (data_len > 0) {
        result['TCP Segment Data:'] = { 
            value: `${data_len} bytes`, 
            offset: tcp_hdr_len, 
            length: data_len 
        };
    }

    return result;
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

function add_ethernet_header (pkt, header_number, offset=0) {

    make_pa("Ethernet Frame", header_number);
    const decode_div = make_div(header_number);
    pkt_decode = decode_ethernet_header(pkt);
    const fields = [];

    for (var k in pkt_decode) {
        const field = pkt_decode[k];
        
		const decode_p = document.createElement("p");
        decode_p.innerHTML = `${k} ${field.value}`;
        decode_div.appendChild(decode_p);

        fields.push({
            label: k,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(k),
            startByte: field.offset
        });
	}

	decode.appendChild(decode_div);

    return {
        className: "Ethernet Frame",
        startByte: offset,
        byteCount: 14,
        fields,
        header_number,
    };
}

function add_vlan_header(pkt, header_number, offset) {

    make_pa("802.1Q Virtual LAN", header_number);
    const decode_div = make_div(header_number);

    const vlan_bytes = pkt.slice(offset, offset + 4);
    const pkt_decode = decode_vlan_header(vlan_bytes);

    const fields = [];

    for (const k in pkt_decode) {
        const field = pkt_decode[k];

        const p = document.createElement('p');
        p.innerHTML = `${k} ${field.value}`;
        decode_div.appendChild(p);

        fields.push({
            label: k,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(k),
            startByte: field.offset
        });
    }

    decode.appendChild(decode_div);

    return {
        className: "802.1Q Virtual LAN",
        startByte: offset,
        byteCount: 4,
        fields, 
        header_number,
    };
}

function add_llc_header (pkt, header_number, offset = 0) {

	make_pa("Logical-Link Control", header_number);
    const decode_div = make_div(header_number);

	pkt_decode = decode_llc_header(pkt);
    const fields = [];

	for (const k in pkt_decode) {
        const field = pkt_decode[k];

        const decode_p = document.createElement("p");
        decode_p.innerHTML = `${k} ${field.value}`;
        decode_div.appendChild(decode_p);

        fields.push({
            label: k,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(k),
            startByte: field.offset
        });
    }

	decode.appendChild(decode_div);

    return {
        className: "Logical-Link Control",
        startByte: offset,
        byteCount: 3,
        fields, 
        header_number,
    };
}

function add_stp_header(pkt, header_number, offset = 0) {

    make_pa("Spanning Tree Protocol", header_number);
    const decode_div = make_div(header_number);

    pkt_decode = decode_stp_header(pkt);
    const fields = [];

    for (const k in pkt_decode) {
        const field = pkt_decode[k];

        const decode_p = document.createElement("p");
        decode_p.innerHTML = `${k} ${field.value}`;
        decode_div.appendChild(decode_p);

        fields.push({
            label: k,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(k),
            startByte: field.offset
        });
    }

    decode.appendChild(decode_div);

    return {
        className: "Spanning Tree Protocol",
        startByte: offset,
        byteCount: pkt.length,
        fields, 
        header_number,
    };
}

function add_arp_header(pkt, header_number, offset = 0) {

    make_pa("Address Resolution Protocol", header_number);
    const decode_div = make_div(header_number);

    const pkt_decode = decode_arp_header(pkt);
    const fields = [];

    for (const k in pkt_decode) {
        const field = pkt_decode[k];

        const decode_p = document.createElement("p");
        decode_p.innerHTML = `${k} ${field.value}`;
        decode_div.appendChild(decode_p);

        fields.push({
            label: k,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(k),
            startByte: field.offset
        });
    }

    decode.appendChild(decode_div);

    return {
        className: "Address Resolution Protocol",
        startByte: offset,
        byteCount: pkt.length,
        fields, 
        header_number,
    };
}

function add_ipv4_header(pkt, header_number, offset = 0) {

    make_pa("Internet Protocol Version 4", header_number);
    const decode_div = make_div(header_number);

    const pkt_decode = decode_ip_header(pkt);
    const fields = [];

    for (const k in pkt_decode) {
        const field = pkt_decode[k];

        const decode_p = document.createElement("p");
        decode_p.innerHTML = `${k} ${field.value}`;
        decode_div.appendChild(decode_p);

        fields.push({
            label: k,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(k),
            startByte: field.offset
        });
    }

    decode.appendChild(decode_div);

    return {
        className: "Internet Protocol Version 4",
        startByte: offset,
        byteCount: 20,
        fields, 
        header_number,
    };
}

function add_icmp_header(pkt, header_number, offset = 0) {

    make_pa("Internet Control Message Protocol", header_number);
    const decode_div = make_div(header_number);

    const pkt_decode = decode_icmp_header(pkt);
    const fields = [];

    for (const k in pkt_decode) {
        const field = pkt_decode[k];

        const decode_p = document.createElement("p");
        decode_p.innerHTML = `${k} ${field.value}`;
        decode_div.appendChild(decode_p);

        fields.push({
            label: k,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(k),
            startByte: field.offset
        });
    }

    const icmp_hdr_len = 8;
    add_payload_info(pkt, icmp_hdr_len, decode_div, fields, offset);

    decode.appendChild(decode_div);

    return {
        className: "Internet Control Message Protocol",
        startByte: offset,
        byteCount: pkt.length,
        fields, 
        header_number,
    };
}

function add_tcp_header(pkt, header_number, offset = 0) {

    make_pa("Transmission Control Protocol", header_number);
    const decode_div = make_div(header_number);

    const pkt_decode = decode_tcp_header(pkt);
    const fields = [];

    for (const k in pkt_decode) {
        const field = pkt_decode[k];

        const decode_p = document.createElement("p");
        decode_p.innerHTML = `${k} ${field.value}`;
        decode_div.appendChild(decode_p);

        fields.push({
            label: k,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(k),
            startByte: field.offset
        });
    }

    decode.appendChild(decode_div);

    return {
        className: "Transmission Control Protocol",
        startByte: offset,
        byteCount: pkt.length,
        fields, 
        header_number,
    };
}

function add_udp_header(pkt, header_number, offset = 0) {

    make_pa("User Datagram Protocol", header_number);
    const decode_div = make_div(header_number);

    const pkt_decode = decode_udp_header(pkt);
    const fields = [];

    for (const k in pkt_decode) {
        const field = pkt_decode[k];

        const decode_p = document.createElement("p");
        decode_p.innerHTML = `${k} ${field.value}`;
        decode_div.appendChild(decode_p);

        fields.push({
            label: k,
            value: field.value,
            offset: field.offset,
            len: field.length,
            className: toHoverKey(k),
            startByte: field.offset
        });
    }

    add_payload_info(pkt, 8, decode_div, fields, offset);

    decode.appendChild(decode_div);

    return {
        className: "User Datagram Protocol",
        startByte: offset,
        byteCount: pkt.length,
        fields, 
        header_number,
    };
}

function add_gre_header(pkt, header_number, offset = 0) {

    make_pa("Generic routing encapsulation (GRE)", header_number);
    const decode_div = make_div(header_number);

    const pkt_decode = decode_gre_header(pkt);
    const fields = [];

    let gre_hdr_len = 8;

    for (const k in pkt_decode) {

        if (k === "GRE_header_length") {
            gre_hdr_len = pkt_decode[k];
            continue;
        }

        const decode_p = document.createElement("p");
        decode_p.innerHTML = `${k} ${pkt_decode[k]}`;
        decode_div.appendChild(decode_p);

        fields.push({
            label: k,
            value: pkt_decode[k],
            offset: 0,
            len: 0,
            className: toHoverKey(k),
            startByte: offset
        });
    }

    add_payload_info(pkt, gre_hdr_len, decode_div, fields, offset);

    decode.appendChild(decode_div);

    return {
        className: "Generic routing encapsulation (GRE)",
        startByte: offset,
        byteCount: gre_hdr_len,
        fields, 
        header_number,
    };
}

function add_payload_info(pkt, header_len, decode_div, fields, offset = 0) {
    const payload_bytes = pkt.length - header_len;
    
    if (payload_bytes > 0) {
        const payload_p = document.createElement('p');
        payload_p.innerHTML = `Data: ${payload_bytes} bytes`;
        decode_div.appendChild(payload_p);
        
        fields.push({
            label: "Data:",
            value: `${payload_bytes} bytes`,
            offset: header_len,
            len: payload_bytes,
            className: "Data",
            startByte: offset + header_len
        });
    }
}

function decode_packet(pkt) {
	
	pkt = pkt.split(/ /);
	let header_number = 5;
	let current_offset = 0;
    const headers = [];

	// Check if packet is long enought
	if (pkt.length < 14){
		console.log("Mimishark: packet is too short");
		return 1;
	}

	const eth = add_ethernet_header(pkt, header_number, current_offset);
    headers.push(eth);
    header_number = header_number + 1;
    current_offset += 14;
	let eth_type = pkt.slice(12,14).join("");

    // VLAN
    if (eth_type === "8100" && pkt.length >= 18) {
        const vlan = add_vlan_header(pkt, header_number, current_offset);
        headers.push(vlan);

        header_number = header_number + 1;
        current_offset += 4;
        eth_type = pkt.slice(16, 18).join("");
    }

	pkt = pkt.slice(current_offset);

	// LLC
	if (parseInt(eth_type, 16) < 1500) {
		const llc = add_llc_header(pkt, header_number, current_offset);
        headers.push(llc);
		header_number = header_number + 1

		let dsap = pkt.slice(0,1).join("");

		// STP
		if (dsap === "42"){
			const stp = add_stp_header(pkt.slice(3), header_number, current_offset + 3);
            headers.push(stp);
		}

		return headers;

	// ARP
	} else if (eth_type === "0806") {
	    const arp = add_arp_header(pkt, header_number, current_offset);
        headers.push(arp);
        return headers;
	} 

	while (true) {

		// IPv4 or IP tunnel
		if (eth_type === "0800" || eth_type === "04") {
			const ip = add_ipv4_header(pkt, header_number, current_offset);

            headers.push(ip);

			header_number++;
            current_offset += ip.byteCount;

			let ip_protocol = pkt.slice(9,10).join("");
			let ip_hdr_len = parseInt(pkt.slice(0,1).toString().split("")[1], 16) * 4;
			let ip_offset = parseInt(pkt.slice(6, 8).join(""), 16) & 8191;

			// Don't parse if IP offset not 0.  
			if (false) {
				return headers;
			}

			// Drop IP header
			pkt = pkt.slice(ip_hdr_len);

			// ICMP
			if (ip_protocol === "01") {
				const icmp = add_icmp_header(pkt, header_number, current_offset);
                headers.push(icmp);
				header_number = header_number + 1;
				break;
			
			// TCP
			} else if (ip_protocol === "06") {
				const tcp = add_tcp_header(pkt, header_number, current_offset);
                headers.push(tcp);
				header_number = header_number + 1;
				break;
			
			// UDP
			} else if (ip_protocol === "11") {
				const udp = add_udp_header(pkt, header_number, current_offset);
                headers.push(udp);
				header_number = header_number + 1;
				break;
			
			// IP
			} else if (ip_protocol === "04") {
				eth_type = ip_protocol;
				continue;

			// GRE
			} else if (ip_protocol === "2f") {
				const gre = add_gre_header(pkt, header_number, current_offset);
                headers.push(gre);

				header_number = header_number + 1;
                current_offset += gre.byteCount;

				// Who is next?
				eth_type = pkt.slice(2,4).join("");
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
	return headers;
}

function renderByteRange({
    decoded,
    startByte,
    endByte,
    spanClass,
    dataArray
}) {
    const container = document.createElement('div');
    let globalOffset = startByte;
    const headerMap = new Map();
    
    while (globalOffset < endByte) {
        const infoByte = getByteOwnership(globalOffset, dataArray, decoded);

        const headerKey = infoByte.headerNumber ? 
            `${infoByte.className}_${infoByte.headerNumber}` : 
            infoByte.className;

        if (!headerMap.has(headerKey)) {
            const headerDiv = document.createElement('div');
            headerDiv.className = toHoverKey(infoByte.className, "", infoByte.headerNumber);
            headerDiv.style.display = 'inline';
            headerMap.set(headerKey, {
                div: headerDiv,
                fieldMap: new Map()
            });
        }
        
        const headerData = headerMap.get(headerKey);
        const headerDiv = headerData.div;
        
        if (infoByte.labels && infoByte.labels.length > 0) {
            const firstLabel = infoByte.labels[0];
            
            const fieldKey = infoByte.headerNumber ? 
                `${firstLabel}_${infoByte.headerNumber}` : 
                firstLabel;

            if (!headerData.fieldMap.has(fieldKey)) {
                const fieldDiv = document.createElement('div');
                fieldDiv.style.display = 'inline';
                
                infoByte.labels.forEach(label => {
                    fieldDiv.classList.add(toHoverKey(label, infoByte.className, infoByte.headerNumber));
                });
                
                headerDiv.appendChild(fieldDiv);
                headerData.fieldMap.set(fieldKey, fieldDiv);
            }
            
            const fieldDiv = headerData.fieldMap.get(fieldKey);
            const byteSpan = document.createElement('span');
            byteSpan.textContent = infoByte.byteValue;
            byteSpan.className = spanClass;
            
            infoByte.labels.forEach(label => {
                byteSpan.classList.add(toHoverKey(label, "", infoByte.headerNumber));
            });
            byteSpan.classList.add(toHoverKey(infoByte.className, "", infoByte.headerNumber));
            
            fieldDiv.appendChild(byteSpan);
        }
        
        globalOffset++;
    }
    
    headerMap.forEach((headerData) => {
        container.appendChild(headerData.div);
    });

    return container;
}

function createByteDivs(pkt, pktData) {
    const rowsEl = document.querySelector('#rows');
    const inputEl = document.querySelector('#bytes');
    const asciiEl = document.querySelector('#ascii');

    rowsEl.replaceChildren();
    inputEl.replaceChildren();
    asciiEl.replaceChildren();

    const decoded = decode_packet(pkt);
    console.log(decoded);
    const bytes = pkt.split(/ /);
    const asciiString = pktData.ascii
        .replace(/doublePrime/g, '"')
        .replace(/singlePrime/g, "'");

    const totalLines = Math.ceil(bytes.length / 16);

    for (let line = 0; line < totalLines; line++) {
        const start = line * 16;
        const end = Math.min(start + 16, bytes.length);

        inputEl.appendChild(
            renderByteRange({
                decoded,
                startByte: start,
                endByte: end,
                spanClass: 'byte',
                dataArray: bytes
            })
        );

        asciiEl.appendChild(
            renderByteRange({
                decoded,
                startByte: start,
                endByte: end,
                spanClass: 'ascii-char',
                dataArray: asciiString.split('')
            })
        );

        const rowP = document.createElement('p');
        rowP.textContent = line.toString().padStart(4, '0');
        rowsEl.appendChild(rowP);
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
            const headerNumber = head.getAttribute('data-header-number');
            const hoverKey = toHoverKey(head.textContent.trim(), "", headerNumber);
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
            const headerNumber = headerLink?.getAttribute('data-header-number');

            const hoverKey = toHoverKey(text, protocolName, headerNumber);
            decodeEl.setAttribute('hoverInfo', hoverKey);
            enableHoverByHoverInfo();
        };
    });
}

function toHoverKey(fieldText, protocolName='', headerNumber='') {
    if (!fieldText || fieldText === null || fieldText === undefined || fieldText === '') {
        return 'unknown';
    }

    const match = fieldText.match(/^([^:=]+)[:=]?/);
    const field = match ? match[1].trim() : fieldText.trim();

    let cleanField = field
        .replace(/\./g, '_')
        .replace(/\s+/g, '_') +  "_" + headerNumber;

    let cleanProtocol = protocolName ? protocolName
        .replace(/\./g, '_')
        .replace(/\s+/g, '_') : '';

    if (cleanField.match(/^\d/)) {
        cleanField = 'field_' + cleanField;
    }
    if (cleanProtocol && cleanProtocol.match(/^\d/)) {
        cleanProtocol = 'proto_' + cleanProtocol;
    }

    if (!cleanProtocol) {
        return CSS.escape(cleanField);
    }

    return CSS.escape(`${cleanProtocol}__${cleanField}`);
}

function decode_ethertype(type_hex) {
    switch (type_hex) {
        case "0800": return "IPv4 (0x0800)";
        case "0806": return "ARP (0x0806)";
        case "8100": return "802.1Q Virtual LAN (0x8100)";

        default:
            if (parseInt(type_hex, 16) < 1500)
                return parseInt(type_hex, 16).toString() + " bytes";

            return type_hex + " (unknown)";
    }
}

function getByteOwnership(i, bytes, decoded) {
    const byteValue = bytes[i];
    const labels = [];
    let className = null;
    let headerNumber;

    decoded.forEach(header => {
        if (i >= header.startByte && i < header.startByte + header.byteCount) {
            if (!className) {
                className = header.className;
            }
            header.fields.forEach(field => {
                const fieldStart = header.startByte + field.offset;
                if (i >= fieldStart && i < fieldStart + field.len) {
                    labels.push(field.label);
                    headerNumber = header.header_number;
                }
            });
        }
    });

    return { byteValue, className, labels, headerNumber };
}
