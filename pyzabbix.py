
#Projeto Original
#https://github.com/adubkov/py-zabbix

#For Zabbix Sender
from decimal import Decimal
import inspect
import socket
import struct

# For python 2 and 3 compatibility
try:
    from StringIO import StringIO
    import ConfigParser as configparser
except ImportError:
    from io import StringIO
    import configparser


class ZabbixResponse(object):
    """The :class:`ZabbixResponse` contains the parsed response from Zabbix.
    """
    def __init__(self):
        self._processed = 0
        self._failed = 0
        self._total = 0
        self._time = 0
        self._chunk = 0
        pattern = (r'[Pp]rocessed:? (\d*);? [Ff]ailed:? (\d*);? '
                   r'[Tt]otal:? (\d*);? [Ss]econds spent:? (\d*\.\d*)')
        self._regex = re.compile(pattern)

    def __repr__(self):
        """Represent detailed ZabbixResponse view."""
        result = json.dumps({'processed': self._processed,
                             'failed': self._failed,
                             'total': self._total,
                             'time': str(self._time),
                             'chunk': self._chunk})
        return result

    def parse(self, response):
        """Parse zabbix response."""
        info = response.get('info')
        res = self._regex.search(info)

        self._processed += int(res.group(1))
        self._failed += int(res.group(2))
        self._total += int(res.group(3))
        self._time += Decimal(res.group(4))
        self._chunk += 1

    @property
    def processed(self):
        return self._processed

    @property
    def failed(self):
        return self._failed

    @property
    def total(self):
        return self._total

    @property
    def time(self):
        return self._time

    @property
    def chunk(self):
        return self._chunk


class ZabbixMetric(object):
    def __init__(self, host, key, value, clock=None):
        self.host = str(host)
        self.key = str(key)
        self.value = str(value)
        if clock:
            if isinstance(clock, (float, int)):
                self.clock = int(clock)
            else:
                raise Exception('Clock must be time in unixtime format')

    def __repr__(self):
        """Represent detailed ZabbixMetric view."""

        result = json.dumps(self.__dict__, ensure_ascii=False)
        return result


class ZabbixSender(object):
    def __init__(self,
                 zabbix_server='127.0.0.1',
                 zabbix_port=10051,
                 use_config=None,
                 chunk_size=250,
                 socket_wrapper=None,
                 timeout=10):

        self.chunk_size = chunk_size
        self.timeout = timeout

        self.socket_wrapper = socket_wrapper
        if use_config:
            self.zabbix_uri = self._load_from_config(use_config)
        else:
            self.zabbix_uri = [(zabbix_server, zabbix_port)]

    def __repr__(self):
        """Represent detailed ZabbixSender view."""

        result = json.dumps(self.__dict__, ensure_ascii=False)
        return result

    def _load_from_config(self, config_file):
        if config_file and isinstance(config_file, bool):
            config_file = '/etc/zabbix/zabbix_agentd.conf'


        #  This is workaround for config wile without sections
        with open(config_file, 'r') as f:
            config_file_data = "[root]\n" + f.read()

        params = {}

        try:
            # python2
            args = inspect.getargspec(
                configparser.RawConfigParser.__init__).args
        except ValueError:
            # python3
            args = inspect.getfullargspec(
                configparser.RawConfigParser.__init__).kwonlyargs

        if 'strict' in args:
            params['strict'] = True

        config_file_fp = StringIO(config_file_data)
        config = configparser.RawConfigParser(**params)
        config.readfp(config_file_fp)
        # Prefer ServerActive, then try Server and fallback to defaults
        if config.has_option('root', 'ServerActive'):
            zabbix_serveractives = config.get('root', 'ServerActive')
        elif config.has_option('root', 'Server'):
            zabbix_serveractives = config.get('root', 'Server')
        else:
            zabbix_serveractives = '127.0.0.1:10051'

        result = []
        for serverport in zabbix_serveractives.split(','):
            if ':' not in serverport:
                serverport = "%s:%s" % (serverport.strip(), 10051)
            server, port = serverport.split(':')
            serverport = (server, int(port))
            result.append(serverport)
        return result

    def _receive(self, sock, count):
        buf = b''

        while len(buf) < count:
            chunk = sock.recv(count - len(buf))
            if not chunk:
                break
            buf += chunk

        return buf

    def _create_messages(self, metrics):
        messages = []

        # Fill the list of messages
        for m in metrics:
            messages.append(str(m))

        return messages

    def _create_request(self, messages):
        msg = ','.join(messages)
        request = '{{"request":"sender data","data":[{msg}]}}'.format(msg=msg)
        request = request.encode("utf-8")
        return request

    def _create_packet(self, request):
        data_len = struct.pack('<Q', len(request))
        packet = b'ZBXD\x01' + data_len + request

        def ord23(x):
            if not isinstance(x, int):
                return ord(x)
            else:
                return x
        return packet

    def _get_response(self, connection):
        response_header = self._receive(connection, 13)

        if (not response_header.startswith(b'ZBXD\x01') or
                len(response_header) != 13):
            result = False
        else:
            response_len = struct.unpack('<Q', response_header[5:])[0]
            response_body = connection.recv(response_len)
            result = json.loads(response_body.decode("utf-8"))
        try:
            connection.close()
        except Exception as err:
            pass

        return result

    def _chunk_send(self, metrics):
        messages = self._create_messages(metrics)
        request = self._create_request(messages)
        packet = self._create_packet(request)

        for host_addr in self.zabbix_uri:

            # create socket object
            connection_ = socket.socket()
            if self.socket_wrapper:
                connection = self.socket_wrapper(connection_)
            else:
                connection = connection_

            connection.settimeout(self.timeout)

            try:
                # server and port must be tuple
                connection.connect(host_addr)
                connection.sendall(packet)
            except socket.timeout:
                connection.close()
                raise socket.timeout
            except Exception as err:
                # In case of error we should close connection, otherwise
                # we will close it after data will be received.
                connection.close()
                raise Exception(err)

            response = self._get_response(connection)

            if response and response.get('response') != 'success':
                raise Exception(response)

        return response

    def send(self, metrics):
        result = ZabbixResponse()
        for m in range(0, len(metrics), self.chunk_size):
            result.parse(self._chunk_send(metrics[m:m + self.chunk_size]))
        return result

