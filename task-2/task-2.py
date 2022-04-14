import re
import socket
import struct
import time

SNTP_SERVER = 'time.windows.com'

# pattern by which the value is searched
PATTERN = re.compile('([+-])(\\d+)')

# Epoch time
TIME_1970 = 2208988800


def sntp_server():
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # timeout - 10 seconds
        client.settimeout(10)

        # SNTP protocol data
        data = '\x1b' + 47 * '\0'
        client.sendto(data.encode('utf-8'), (SNTP_SERVER, 123))
        data, address = client.recvfrom(1024)

        # required data is located in the 11th element of the array
        result_time = struct.unpack('!12I', data)[10]

        with open('../resources-2/config.txt', 'r', encoding='utf-8') as file:
            try:
                seconds = re.match(PATTERN, file.readline())
                if seconds.group(1) == '+':
                    result_time += int(seconds.group(2)) - TIME_1970
                elif seconds.group(1) == '-':
                    result_time -= int(seconds.group(2)) + TIME_1970
                print('Current time = %s' % time.ctime(result_time))
            except AttributeError:
                print('Incorrect data format!')

    except ConnectionError:
        print('No connection!')
    except TimeoutError:
        print('Timeout expired!')


if __name__ == '__main__':
    sntp_server()
