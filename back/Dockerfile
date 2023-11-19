FROM ubuntu:22.04

RUN apt-get update \
&& apt-get install -y --no-install-recommends \
    curl \
    dnsutils \
    netcat \
    openssh-client \
    ifupdown \
    iproute2 \
    iptables \
    traceroute \
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
 

WORKDIR /app
ADD ./requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt
ADD ./ENTRYPOINT.sh /app/ENTRYPOINT.sh
RUN chmod +x ENTRYPOINT.sh
ADD ./src /app
ENTRYPOINT ["/app/ENTRYPOINT.sh"]
