FROM ubuntu:24.04

ENV PIP_BREAK_SYSTEM_PACKAGES=1

RUN apt-get update \
&& apt-get install -y --no-install-recommends \
    curl \
    dnsutils \
    netcat-openbsd \
    openssh-client \
    ifupdown \
    iproute2 \
    iptables \
    traceroute \
    iputils-ping \
    mininet \
    net-tools \
    kmod \
    bridge-utils \
    tcpdump \
    git\
    python3-pip \
    dnsmasq \
    isc-dhcp-client \
    python3-setuptools \
    gcc \
    make \
    libpcap-dev \
    libbsd-dev \
    openvswitch-switch \
 && pip3 install --upgrade --ignore-installed pip \
 && rm -rf /var/lib/apt/lists/* \
 && touch /etc/network/interfaces \
 && mkdir /opt/mininet_dependencies

RUN git clone https://github.com/mimi-net/mimidump.git \
    && cd mimidump && git checkout 971ff5236 && make prefix=/usr install && cd .. && rm -rf mimidump

WORKDIR /app
ADD ./requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt
ADD ./ovs-init.sh /app/ovs-init.sh
ADD ./ENTRYPOINT.sh /app/ENTRYPOINT.sh
RUN chmod +x ovs-init.sh ENTRYPOINT.sh
ADD ./src /app

ENTRYPOINT ["/app/ENTRYPOINT.sh"]
