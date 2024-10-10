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
    python3-setuptools \
    gcc \
    make \
    libpcap-dev \
    libbsd-dev \
 && rm -rf /var/lib/apt/lists/* \
 && touch /etc/network/interfaces \
 && mkdir /opt/mininet_dependencies

RUN git clone https://github.com/mimi-net/mimidump.git \
    && cd mimidump && git checkout 32e6e5e && make prefix=/usr install && cd .. && rm -rf mimidump

WORKDIR /app
ADD ./requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt
ADD ./ENTRYPOINT.sh /app/ENTRYPOINT.sh
RUN chmod +x ENTRYPOINT.sh
ADD ./src /app

ENTRYPOINT ["/app/ENTRYPOINT.sh"]
