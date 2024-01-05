import unittest
from unittest.mock import MagicMock, call, patch
import sys, os
import subprocess

cur_dir=os.path.dirname(os.path.abspath(__file__))
proj_root=os.path.abspath(os.path.join(cur_dir,'..'))
sys.path.append(proj_root)

from jobs import dhcp_server, dhcp_client, mask_to_byte, parse_ip_route_show_output
from network import Job
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import Host

subprocess.run(['sudo', 'mn', '-c'], capture_output=True, text=True)

def create_mininet_topology():
    net = Mininet()

    host = net.addHost('h1')
    switch = net.addSwitch('s1')
    net.addLink(host, switch)
    net.start()
    return net


class TestDHCPFunctions(unittest.TestCase):
    def setUp(self):
        # Создаем макет (mock) для host
        self.mock_host = MagicMock()

        # Создаем экземпляр Job для тестов
        self.job_info = Job(id='job_id_1', level=1, job_id=105, host_id='h1', print_cmd='', arg_1='10.0.0.10,10.0.0.20', arg_2=16, arg_3='10.0.0.1')

        self.net = create_mininet_topology()

    def tearDown(self):
        # Очищаем Mininet топологию в tearDown
        self.net.stop()

    def get_mininet_host(self, host_id):
        # Вспомогательная функция для получения хоста из Mininet
        return self.net.get(host_id)

    def test_dhcp_server(self):
        # Тестируем функцию dhcp_server
        dhcp_server(self.job_info, self.mock_host)

        # Проверяем, что методы и команды были вызваны с ожидаемыми параметрами
        expected_commands = [
            call('service dnsmasq stop'),
            call('dnsmasq --dhcp-range=10.0.0.10,10.0.0.20,255.255.0.0 --dhcp-option=3,10.0.0.1')
        ]
        self.mock_host.cmd.assert_has_calls(expected_commands)


    @patch('jobs.parse_ip_route_show_output', return_value=('10.0.0.1', '255.255.255.0', '10.0.0.254'))
    def test_dhcp_client(self, parse_ip_route_mock):
        # Тестируем функцию dhcp_client
        self.mock_host.intf().name = 'h1-eth0'

        # Вызываем функцию
        dhcp_client(self.job_info, self.mock_host)

        # Создаем ожидаемые вызовы
        expected_commands = [
            call('ifconfig h1-eth0 0'),
            call('timeout -k 0 30 dhclient -v -4 h1-eth0'),
            call('ip route show'),
            call('route add default gw 10.0.0.254')
        ]

        # Проверяем, что все вызовы были выполнены в ожидаемом порядке
        self.mock_host.cmd.assert_has_calls(expected_commands)

    def test_mask_to_byte(self):
        result = mask_to_byte(16)
        self.assertEqual(result, '255.255.0.0')

    def test_parse_ip_route_show_output(self):
        output = 'default via 192.168.1.1 dev eth0\n 192.168.1.0/24 dev eth0 proto kernel scope link src 192.168.1.100'
        ip, netmask, gateway = parse_ip_route_show_output(output)
        self.assertEqual(ip, '192.168.1.100')
        self.assertEqual(netmask, '24') 
        self.assertEqual(gateway, '192.168.1.1')

if __name__ == '__main__':
    unittest.main()
