FROM ubuntu:26.04

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
    && cd mimidump && git checkout 854a3b0a1f712506a0d1a2d626be62ada9ffefe7 && make prefix=/usr install && cd .. && rm -rf mimidump

WORKDIR /app
COPY pyproject.toml uv.lock /app/
COPY back/pyproject.toml /app/back/pyproject.toml
COPY front/pyproject.toml /app/front/pyproject.toml
RUN pip3 install uv && uv sync --frozen --no-dev --project back
ENV PATH="/app/.venv/bin:$PATH"
COPY back/ovs-init.sh /app/ovs-init.sh
COPY back/ENTRYPOINT.sh /app/ENTRYPOINT.sh
RUN chmod +x ovs-init.sh ENTRYPOINT.sh
COPY back/src /app

ENTRYPOINT ["/app/ENTRYPOINT.sh"]
