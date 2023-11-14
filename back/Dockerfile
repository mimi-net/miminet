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
ADD ./ENTRYPOINT.sh /app/ENTRYPOINT.sh
RUN chmod +x ENTRYPOINT.sh
ADD ./requirements.txt /app/requirements.txt
RUN pip3 install -r requirements.txt
ADD . /app
ENTRYPOINT ["/app/ENTRYPOINT.sh"]
