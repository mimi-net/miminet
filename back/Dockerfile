FROM ubuntu:22.04

RUN apt-get update \
&& apt-get install -y --no-install-recommends \
    curl \
    dnsutils \
    openssh-client \
    ifupdown \
    iproute2 \
    iptables \
    iputils-ping \
    mininet \
    net-tools \
    bridge-utils \
    tcpdump \
    git\
    python3-pip \
    python3-setuptools \
 && rm -rf /var/lib/apt/lists/* \
 && touch /etc/network/interfaces \
 && mkdir /opt/mininet_dependencies
 
RUN pip3 install --upgrade git+https://github.com/mimi-net/ipmininet.git@v1.0.0

WORKDIR /app
ADD . /app
RUN chmod +x /app/ENTRYPOINT.sh
RUN pip3 install -r /app/requirements.txt
ENTRYPOINT ["/app/ENTRYPOINT.sh"]
