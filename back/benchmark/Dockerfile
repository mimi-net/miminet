FROM ubuntu:22.04

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
 && pip3 install --upgrade pip \
 && rm -rf /var/lib/apt/lists/* \
 && touch /etc/network/interfaces \
 && mkdir /opt/mininet_dependencies

RUN git clone https://github.com/mimi-net/mimidump.git \
    && cd mimidump && git checkout 32e6e5e && make prefix=/usr install && cd .. && rm -rf mimidump

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt
COPY src /app

ENV celery_concurrency=1
ENV queue_names=benchmark-queue

# Create startup script for benchmarking
RUN echo '#!/bin/bash\n\
set -e\n\
# Kill any existing ovs-vswitchd processes\n\
killall ovs-vswitchd ovsdb-server 2>/dev/null || true\n\
sleep 1\n\
# Start Open vSwitch without loading kernel module (use host module)\n\
/usr/share/openvswitch/scripts/ovs-ctl start --no-insert-kernel-module 2>&1 || true\n\
sleep 2\n\
# Cleanup any previous mininet state\n\
mn -c > /dev/null 2>&1 || true\n\
# Execute the command\n\
exec "$@"\n\
' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["bash"]
