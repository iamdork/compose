import dork_compose.plugin
from compose.cli.docker_client import docker_client


class Subnet:
    """
    Represents one subnet and provides useful calculation methods.
    """

    def __init__(self, subnet="", ip=[], cidr=None):
        """
        Create a new subnet either by parsing the ip/cidr notation or setting
        an ip and the cidr.

        :param subnet: A string with ip/cidr to create a new subnet
        :param ip: A ip to create a new subnet, cidr is required as well.
        :param cidr: A cidr to create a new subnet, the ip is required as well.
        """
        if subnet != "":
            tmp = subnet.split('/')
            self.__cidr = int(tmp[1])

            ip = [int(x) for x in tmp[0].split('.')]
        elif len(ip) == 4 and cidr != None:
            self.__cidr = cidr

        self.__net = Subnet.__ip_and(ip, self.net_mask)

    def overlaps(self, subnet):
        """
        Checks if the given subnet intersects with this subnet.
        :param subnet: A Subnet object.
        :return: True if they overlap, False if not.
        """
        if subnet.cidr < self.cidr:
            cidr = subnet.cidr
        else:
            cidr = self.cidr

        if cidr <= 8:
            to_check = 0
        elif 8 < cidr <= 16:
            to_check = 1
        elif 16 < cidr <= 24:
            to_check = 2
        else:
            to_check = 3

        for x, y in zip(subnet.net, self.net)[0:to_check]:
            if x != y:
                return False

        if (self.last[to_check] < subnet.first[to_check]) or \
                (self.first[to_check] > subnet.last[to_check]):
            return False
        else:
            return True

    @property
    def cidr(self):
        """
        Returns the CIDR
        """
        return self.__cidr

    @property
    def net(self):
        """
        Returns the net
        """
        return self.__net

    @property
    def net_mask(self):
        """
        Calculates & returns the net mask out of the CIDR.
        https://stackoverflow.com/a/43904598/4265508
        """
        mask = (0xffffffff >> (32 - self.cidr)) << (32 - self.cidr)

        return Subnet.__create_mask(mask)

    @property
    def wild_card(self):
        """
        Calculates & returns the wild card mask out of the CIDR.
        """
        mask = ~((0xffffffff >> (32 - self.cidr))
                 << (32 - self.cidr)) & 0xffffffff

        return Subnet.__create_mask(mask)

    @property
    def first(self):
        """
        Returns the first ip of this subnet.
        """
        return self.__net

    @property
    def last(self):
        """
        Returns the last ip of this subnet
        """
        return Subnet.__add_ips(self.net, self.wild_card)

    @property
    def next_net(self):
        """
        Returns the next available subnet with the same subnet mask.
        :return: A subnet object
        """
        if self.cidr <= 8:
            part = 0
        elif 8 < self.cidr <= 16:
            part = 1
        elif 16 < self.cidr <= 24:
            part = 2
        else:
            part = 3

        to_add = [0] * part
        to_add.append(1)
        to_add = to_add + [0] * (4 - len(to_add))

        tmp = Subnet.__add_ips(self.last, to_add)

        ip = []
        carry = 0
        for x in reversed(tmp):
            if carry > 0:
                sum = x + carry
                if sum > 255:
                    ip.insert(0, 0)
                else:
                    ip.insert(0, sum)
                    carry = 0
            else:
                if x > 255:
                    ip.insert(0, 0)
                    carry = 1
                else:
                    ip.insert(0, x)

        return Subnet(ip=ip, cidr=self.cidr)

    def __str__(self):
        net = ".".join(str(x) for x in self.net)
        return "%s/%i" % (net, self.cidr)

    @staticmethod
    def __ip_and(ip1, ip2):
        return [x & y for x, y, in zip(ip1, ip2)]

    @staticmethod
    def __add_ips(ip1, ip2):
        return [x + y for x, y in zip(ip1, ip2)]

    @staticmethod
    def __create_mask(mask):
        return [(0xff000000 & mask) >> 24,
                (0x00ff0000 & mask) >> 16,
                (0x0000ff00 & mask) >> 8,
                (0x000000ff & mask)]


class Plugin(dork_compose.plugin.Plugin):
    """
    This allows to override the default subnet pool for projects.
    """

    def initializing(self, project, service_names=None):
        # Get a free subnet
        subnet = self.__get_free_subnet()

        # Inject it into network config.
        project.networks.networks['default'].ipam = {
            'Driver': 'default',
            'Config': [
                {'Subnet': str(subnet)},
            ]
        }

    def __get_free_subnet(self):
        client = docker_client(self.env)

        subnets = []
        # List all networks and save them as Subnet object into a list.
        for network in client.networks():
            for config in network['IPAM']['Config']:
                subnets.append(Subnet(config['Subnet']))

        # Find a suitable network, by checking going through all possibilities
        # until a network doesn't overlaps with an existing one.
        # todo: Improve algorithm, so that it doesn't searches forever.
        res = self.default_subnet
        overlaps = True
        while overlaps:
            # Test if the selected network overlaps with existing ones.
            for subnet in subnets:
                # if it overlaps, then set overlaps then get the next possible
                # networks and stop testing against the rest of the existing
                # networks.
                if subnet.overlaps(res):
                    overlaps = True
                    res = res.next_net
                    break
                else:
                    overlaps = False

        return res

    @property
    def default_subnet(self):
        return Subnet(self.env.get('DORK_SUBNET_DEFAULT', '172.20.0.0/24'))
