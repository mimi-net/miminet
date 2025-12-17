let newdata = data.replace(/&#39;/g, '"'); 
let pcap_data = JSON.parse(newdata);
let tds = document.querySelectorAll('tbody tr');
let input = document.querySelector('#bytes');
let rows = document.querySelector('#rows');
let ascii = document.querySelector('#ascii');
let decode = document.querySelector('#decode');
{
	tds[0].classList.toggle('selected');
	tds[0].classList.add('no-hover');
	decode_packet(pcap_data[0].bytes);

	var string = pcap_data[0]['bytes'];

    for (var b = 0; b < (string.length) / 47; b++) {
        var elem1 = document.createElement("p");
        elem1.innerHTML = b.toString().padStart(4, '0');
        rows.appendChild(elem1);
        var elem2 = document.createElement("p");
        elem2.innerHTML = pcap_data[0]['bytes'].substring(b * 47 + b, (b * 47) + 47 + b);
        input.appendChild(elem2);
        var elem3 = document.createElement("p");
        elem3.style.whiteSpace="nowrap";
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
	    elem3.style.whiteSpace="nowrap";
            var ascii_with_prime = pcap_data[i - 1]['ascii'].replace('doublePrime', '"').replace('singlePrime', "'");
            elem3.innerHTML = ascii_with_prime.substring(b * 16 + b, (b * 16) + 16 + b);
            ascii.appendChild(elem3);
        }
		decode_packet(pcap_data[i - 1].bytes);
    };
});

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

function hex_to_ip (ip_hex) {

	let ip_str = [];

	for (var i = 0; i < ip_hex.length; i++) {
		ip_str[i] = parseInt(ip_hex[i], 16);
	}

	return ip_str.join(".");
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
		"Destination:" : eth_hdr.slice(0,6).join(":"),
		"Source:" : eth_hdr.slice(6,12).join(":"),
		"Type/Length:" : eth_type_length_string,
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
		"DSAP:" : dsap_string,
		"SSAP:" : ssap_string,
		"Control field:" : llc_hdr.slice(2,3).join("")
	};
}

function decode_stp_header (stp_hdr) {

	let protocol_id = stp_hdr.slice(0,2).join("");
	let version = parseInt(stp_hdr.slice(2,3).join(""), 16);
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

	// Handle different protocol versions
	let version_string = "";
	if (version === 0) {
		version_string = "Spanning Tree (0)";
	} else if (version === 2) {
		version_string = "Rapid Spanning Tree (2)";
	} else if (version === 3) {
		version_string = "Multiple Spanning Tree (3)";
	} else {
		version_string = "Spanning Tree (" + version.toString() + ")";
	}

	if (bpdu_type === "00") {
		bpdu_type_string = "Configuration (0x00)";
	} else if (bpdu_type === "02") {
		if (version === 3) {
			bpdu_type_string = "MST BPDU (0x02)";
		} else {
			bpdu_type_string = "RST BPDU (0x02)";
		}
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

	let result = {
		"Protocol Identifier:" : protocol_id_string,
		"Protocol Version Identifier:" : version_string,
		"BPDU Type:" : bpdu_type_string,
		"BPDU flags:" : bpdu_flags_string,
		"Root Identifier:" : root_identifier_string,
		"Root Path Cost:" : parseInt(stp_hdr.slice(13, 17).join(""), 16).toString(),
		"Bridge Identifier:" : bridge_identifier_string,
		"Port identifier:" : "0x" + stp_hdr.slice(25, 27).join(""),
		"Message Age:" : (parseInt(stp_hdr.slice(27,29).join(""), 16)/256).toString(),
		"Max Age:" : (parseInt(stp_hdr.slice(29,31).join(""), 16)/256).toString(),
		"Hello Time:" : (parseInt(stp_hdr.slice(31,33).join(""), 16)/256).toString(),
		"Forward Delay:" : (parseInt(stp_hdr.slice(33,35).join(""), 16)/256).toString(),
	};

	// Add MSTP-specific fields if version is 3
	if (version === 3 && stp_hdr.length > 35) {
		result["Version 1 Length:"] = parseInt(stp_hdr.slice(35,36).join(""), 16).toString();
		if (stp_hdr.length > 36) {
			result["Version 3 Length:"] = parseInt(stp_hdr.slice(36,38).join(""), 16).toString();
		}
	}

	return result;
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
		"Hardware type:" : hw_type_string,
		"Protocol type:" : proto_type_string,
		"Hardware size:" : arp_hdr.slice(4,5).toString(),
		"Protocol size:" : arp_hdr.slice(5,6).toString(),
		"Opcode:" : opcode_string,
		"Sender MAC address:" : arp_hdr.slice(8,14).join(":"),
		"Sender IP address:" : hex_to_ip(arp_hdr.slice(14, 18)),
		"Target MAC address:" : arp_hdr.slice(18, 24).join(":"),
		"Target IP address:" : hex_to_ip(arp_hdr.slice(24, 28)),
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
		"xxxx .... = " : ip_ver_string,
		".... xxxx = " : ip_hdr_len_string,
		"Differentiated Service Field:" : ip_hdr.slice(1,2).toString(),
		"Total Length:" : parseInt(ip_hdr.slice(2, 4).join(""), 16).toString(),
		"Identification:" : "0x" + ip_hdr.slice(4, 6).join(""),
		"Flag and Fragment Offset:" : ip_hdr.slice(6, 8).join(""),
		"...x xxxx xxxx xxxx = Fragment Offset:" : (ip_flag_and_offset & 8191) * 8,
		"Time to Live:" : parseInt(ip_hdr.slice(8,9), 16).toString(),
		"Protocol:" : ip_protocol_string,
		"Header Checksum:" : "0x" + ip_hdr.slice(10,12).join(""),
		"Source Address:" : hex_to_ip(ip_hdr.slice(12,16)),
		"Destination Address:" : hex_to_ip(ip_hdr.slice(16,20)),
	};
}

function decode_icmp_header (icmp_hdr) {

	let icmp_type = icmp_hdr.slice(0,1).join("");
	let icmp_type_string = "";
	
	if (icmp_hdr.length < 8) {
		console.log("Mimishark: ICMP header is too small");
		return {};
	}

	if (icmp_type === "08") {
		icmp_type_string = "8 (Echo (ping) request)";

		return {
			"Type:" : icmp_type_string,
			"Code:" : icmp_hdr.slice(1,2).join(""),
			"Checksum:" : "0x" + icmp_hdr.slice(2, 4).join(""),
			"Identifier:" : "0x" + icmp_hdr.slice(4, 6).join(""),
			"Sequence Number:" : "0x" + icmp_hdr.slice(6, 8).join(""),
		};
	} else if (icmp_type === "00") {
		icmp_type_string = "0 (Echo (ping) reply)";

		return {
			"Type:" : icmp_type_string,
			"Code:" : icmp_hdr.slice(1,2).join(""),
			"Checksum:" : "0x" + icmp_hdr.slice(2, 4).join(""),
			"Identifier:" : "0x" + icmp_hdr.slice(4, 6).join(""),
			"Sequence Number:" : "0x" + icmp_hdr.slice(6, 8).join(""),
		};
	} else if (icmp_type === "03") {

		let icmp_code = icmp_hdr.slice(1, 2).join("");
		let icmp_code_string = "";

		icmp_type_string = "3 (Destination unreachable)";

		if (icmp_code === "00") {
			icmp_code_string = "0 (Network unreachable)";
		} else if (icmp_code === "01") {
			icmp_code_string = "1 (Host unreachable)";
		} else if (icmp_code === "03") {
			icmp_code_string = "3 (Port unreachable)";
		} else if (icmp_code === "04") {
			icmp_code_string = "4 (Fragmentation needed and DF set)";
		}

		return {
			"Type:" : icmp_type_string,
			"Code:" : icmp_code_string,	
			"Checksum:" : "0x" + icmp_hdr.slice(2, 4).join(""),
			"Unused:" : icmp_hdr.slice(4, 8).join(""),
		};
	} else if (icmp_type === "05") {

		let icmp_code = icmp_hdr.slice(1, 2).join("");
		let icmp_code_string = "";

		if (icmp_code === "00") {
			icmp_code_string = "0 (Redirect for the Network)";
		} else if (icmp_code === "01") {
			icmp_code_string = "1 (Redirect for the Host)";
		} else if (icmp_code === "02") {
			icmp_code_string = "2 (Redirect for the Type of Service and Network)";
		} else if (icmp_code === "03") {
			icmp_code_string = "3 (Redirect for the Type of Service and Host)";
		}

		icmp_type_string = "5 (Redirect Message)";

		return {
			"Type:" : icmp_type_string,
			"Code:" : icmp_code_string,
			"Checksum:" : "0x" + icmp_hdr.slice(2, 4).join(""),
			"Gateway:" : hex_to_ip(icmp_hdr.slice(4, 8)),
		};
	} else if (icmp_type === "0b") {

		let icmp_code = icmp_hdr.slice(1, 2).join("");
		let icmp_code_string = "";

		if (icmp_code === "00") {
			icmp_code_string = "0 (Time To Live exceeded in transit)";
		} else if (icmp_code === "01") {
			icmp_code_string = "1 (Fragment reassembly time exceeded)";
		}

		icmp_type_string = "11 (Time To Live Exceeded)";

		return {
			"Type:" : icmp_type_string,
			"Code:" : icmp_code_string,
			"Checksum:" : "0x" + icmp_hdr.slice(2, 4).join(""),
			"Unused:" : icmp_hdr.slice(4, 8).join(""),
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
		"Source Port:" : parseInt(udp_hdr.slice(0,2).join(""), 16).toString(),
		"Destination Port:" : parseInt(udp_hdr.slice(2,4).join(""), 16).toString(),	
		"Length:" : parseInt(udp_hdr.slice(4,6).join(""), 16).toString(),
		"Checksum:" : "0x" + udp_hdr.slice(0,2).join(""),
	};
}

function decode_tcp_header (tcp_hdr) {

	let tcp_hdr_len = parseInt(tcp_hdr.slice(12, 13).join(""), 16) >> 4;

	if (tcp_hdr.length < 20) {
		console.log("Mimishark: TCP header is too small");
		return {};
	}


	return {
		"Source Port:" : parseInt(tcp_hdr.slice(0,2).join(""), 16).toString(),
		"Destination Port:" : parseInt(tcp_hdr.slice(2,4).join(""), 16).toString(),
		"Sequence Number:" : parseInt(tcp_hdr.slice(4,8).join(""), 16).toString(),
		"Acknowledge Number:" : parseInt(tcp_hdr.slice(8,12).join(""), 16).toString(),
		"xxxx .... = Header Length: " : (tcp_hdr_len * 4) + " bytes (" + tcp_hdr_len + ")",
		"Flags:" : "0x" + tcp_hdr.slice(13, 14).join(""),
		"Window:" : parseInt(tcp_hdr.slice(14, 16).join(""), 16).toString(),
		"Checksum:" : "0x" + tcp_hdr.slice(16,18).join(""),
		"Urgent Pointer:" : "0x" + tcp_hdr.slice(18,20).join(""),
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


	let ret_val =  {
		"x... .... .... .... = checksum bit: " : Boolean(C).toString(),
		".X.. .... .... .... = routing bit: " : Boolean(R).toString(),
		"..X. .... .... .... = key bit: " : Boolean(K).toString(),
		"...X .... .... .... = sequence number bit: " : Boolean(S).toString(),
		".... X... .... .... = strict source route bit: " : Boolean(s).toString(),
		".... .XXX .... .... = recursion control: " : Recur.toString(),
		".... .... XXXX X... = flags: " : Flags.toString(),
		".... .... .... .XXX = version: " : Version.toString(),
		"Protocol type: " : protocol_type_string,
	};

	if (C) {
		ret_val["Checksum"] = parseInt(gre_hdr.slice(4,6).join(""), 16).toString();
		ret_val["Offset"] = parseInt(gre_hdr.slice(6,8).join(""), 16).toString();
		gre_hdr_length += 8;
	}

	if (K) {
		ret_val["Key"] = parseInt(gre_hdr.slice(8,12).join(""), 16).toString();
		gre_hdr_length += 4;
	}

	if (S) {
		ret_val["Sequence number"] = parseInt(gre_hdr.slice(12,16).join(""), 16).toString();
		gre_hdr_length += 4;
	}
	
	ret_val["GRE_header_length"] = gre_hdr_length;
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
		decode_p.innerHTML = k + " " + pkt_decode[k];
		decode_div.appendChild(decode_p);
	}

	decode.appendChild(decode_div);
}

function add_stp_header (pkt, header_number) {
	// Determine protocol type based on version
	let version = parseInt(pkt.slice(2,3).join(""), 16);
	let protocol_name = "Spanning Tree Protocol";
	
	if (version === 2) {
		protocol_name = "Rapid Spanning Tree Protocol";
	} else if (version === 3) {
		protocol_name = "Multiple Spanning Tree Protocol";
	}

	make_pa(protocol_name, header_number);
	decode_div = document.createElement("div");
	decode_div.classList.add("collapse", "decode_body", "decode_width");
	decode_div.id = "collapseDecode" + header_number;

	pkt_decode = decode_stp_header(pkt);

	for (var k in pkt_decode) {
		let decode_p = document.createElement("p");
		decode_p.innerHTML = k + " " + pkt_decode[k];
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
		decode_p.innerHTML = k + " " + pkt_decode[k];
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
		decode_p.innerHTML = k + " " + pkt_decode[k];
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
		decode_p.innerHTML = k + " " + pkt_decode[k];
		decode_div.appendChild(decode_p);
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
		decode_p.innerHTML = k + " " + pkt_decode[k];
		decode_div.appendChild(decode_p);
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
		decode_p.innerHTML = k + " " + pkt_decode[k];
		decode_div.appendChild(decode_p);
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

	decode.appendChild(decode_div);

	return gre_hdr_len;
}

function decode_packet(pkt) {
	
	pkt = pkt.split(/ /);
	let header_number = 5;
	let decode_div;
	let pkt_decode;

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

	for (var k in pkt_decode) {
		let decode_p = document.createElement("p");
		decode_p.innerHTML = k + " " + pkt_decode[k];
		decode_div.appendChild(decode_p);
    	}

	decode.appendChild(decode_div);
	header_number = header_number + 1;

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

