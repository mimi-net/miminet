if [ -d ipmininet ]; then
  sudo rm -rf ipmininet
fi

# Если есть OpenFlow, то эта директория уже существует и
# по ней ipmininet определяет скачан ли mininet
if [ ! -d /opt/mininet_dependencies ]; then
  sudo mkdir /opt/mininet_dependencies
fi

#cd ipmininet
#sudo python3 setup.py bdist_wheel
#sudo pip3 install dist/ipmininet-1.1-py3-none-any.whl

pip3 install --upgrade git+https://github.com/mimi-net/ipmininet.git@v1.0.0
