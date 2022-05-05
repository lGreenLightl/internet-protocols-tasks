import time
import binascii
import socket
import pickle


def get_cur_seconds():
    return int(round(time.time()))


previous_time = get_cur_seconds()
cache = {}


class Record:
    def __init__(self, data, record_type, ttl):
        self._data = data
        self._data_len = len(data) // 2
        self._type = record_type
        self._ttl = int(ttl, 16)
        self.valid = self._ttl + get_cur_seconds()

    def generate_response(self):
        return ('c00c' + self._type + '0001' +
                hex(self.valid - get_cur_seconds())[2:].rjust(8, '0') +
                hex(self._data_len)[2:].rjust(4, '0') + self._data), self.valid > get_cur_seconds()


def send_dgram(data, server_address, port):
    data = data.replace('\n', '').replace(' ', '')
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2)

    try:
        sock.sendto(binascii.unhexlify(data), (server_address, port))
        response, _ = sock.recvfrom(4096)
    except ConnectionError:
        print('No connection!')
        return None
    except TimeoutError:
        print('Timeout expired!')
        return None
    return binascii.hexlify(response).decode('utf-8')


def get_cache_responses(data_list):
    result = []
    for element in data_list:
        data, is_valid = element.generate_response()
        if is_valid:
            result.append(data)
    return ''.join(result), len(result)


def clear_cache():
    global previous_time
    cur_time = get_cur_seconds()
    if cur_time - previous_time >= 120:
        del_keys = []
        for keys, values in cache.items():
            for element in values:
                if element.valid <= cur_time:
                    del element
            if len(values) == 0:
                del_keys.append(keys)
        for keys in del_keys:
            del cache[keys]
        previous_time = get_cur_seconds()

    save_state()


def get_name(request, start=24):
    name = []
    offset = 0

    while True:
        index = start + offset
        raw_str = request[index:index + 4]

        if int(raw_str, 16) >= 49152:
            link = str(bin(int(raw_str, 16)))[2:]
            link = int(link[2:], 2) * 2
            rest, offset = get_name(request, link)
            name.append(rest)
            name.append('.')
            break

        length = int(request[index:index + 2], 16)

        if length == 0:
            break

        i = 2
        while i <= length * 2:
            decoded_str = chr(int(request[index + i:index + i + 2], 16))
            name.append(decoded_str)
            i += 2

        name.append('.')
        offset += length * 2 + 2

    name = ''.join(name[:-1])
    return name, offset


def retrieve_name(request, index):
    link = str(bin(int(request[index:index + 4], 16)))[2:]
    result, _ = get_name(request, int(link[2:], 2) * 2)
    return result


def parse_server_response(request):
    if request is None:
        return None

    header = request[0:24]
    question = request[24:]
    name, offset = get_name(request)
    record_type = question[offset - 8:offset - 4]
    char_count = len(name) - name.count('.')
    question_len = char_count * 2 + (name.count('.') + 2) * 2
    response = request[24 + question_len + 8:]
    an_count = int(header[12:16], 16)
    ns_count = int(header[16:20], 16)
    ar_count = int(header[20:24], 16)
    diff_counts = [an_count, ns_count, ar_count]
    other_data = response

    for count in diff_counts:
        answers = []
        prev_name = name
        cur_name = name

        for i in range(count):
            cur_name = retrieve_name(request, request.index(other_data))
            record_type = other_data[4:8]
            ttl = other_data[12:20]
            data_len = int(other_data[20:24], 16) * 2
            data = other_data[24:24 + data_len]
            link = str(bin(int(data[-4:], 16)))[2:]

            if record_type == '0002' and data[-2:] != '00' and link[:2] == '11':
                link = int(link[2:], 2) * 2
                _, offset = get_name(request[link:], 0)
                ending = request[link:link + offset] + '00'
                data = data[:-4] + ending

            answer = Record(data, record_type, ttl)
            other_data = other_data[24 + data_len:]

            if cur_name != prev_name:
                cache[(cur_name, record_type)] = [answer]
                answers = []
            else:
                answers.append(answer)

            prev_name = cur_name

        if len(answers) != 0:
            cache[(cur_name, record_type)] = answers

    save_state()
    return request


def parse_server_request(request):
    header = request[0:24]
    question = request[24:]
    name, _ = get_name(request)
    record_type = question[-8:-4]

    if (name, record_type) in cache:
        data, count = get_cache_responses(cache[(name, record_type)])

        if count != 0:
            transaction_id = header[0:4]
            flags = '8180'
            qd_count = header[8:12]
            an_count = hex(count)[2:].rjust(4, '0')
            ns_count = header[16:20]
            ar_count = header[20:24]
            new_head = transaction_id + flags + qd_count + an_count + ns_count + ar_count

            print(f'Record from cache -> {name}, {handle_type(record_type)}')

            return new_head + question + data

    print(f'Record from server -> {name}, {handle_type(record_type)}')

    return parse_server_response(send_dgram(request, '94.140.14.14', 53))


def handle_type(record_type):
    if record_type == '0001':
        return 'A'
    elif record_type == '0002':
        return 'NS'
    elif record_type == '000c':
        return 'PTR'
    elif record_type == '001c':
        return 'AAAA'
    else:
        return 'unknown type'


def save_state():
    with open('../resources-4/cache', 'wb+') as file:
        pickle.dump(cache, file)


def dns_server():
    global cache
    try:
        with open('../resources-4/cache', 'rb') as file:
            cache = pickle.load(file)
    except FileNotFoundError:
        print('Cache file not found!')
    except EOFError:
        cache = {}

    clear_cache()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 53))
    while True:
        try:
            data, address = sock.recvfrom(4096)
            data = binascii.hexlify(data).decode('utf-8')
            server_response = parse_server_request(data)
            if server_response is not None:
                sock.sendto(binascii.unhexlify(server_response), address)
            clear_cache()
        except KeyboardInterrupt:
            answer = None
            while answer not in ['y', 'n']:
                print('Shut down server?[y/n]', end=' ')
                answer = input()
            if answer == 'n':
                continue
            if answer == 'y':
                save_state()
                exit(0)
        except ConnectionError:
            print('No connection!')
        except TimeoutError:
            print('Timeout expired!')


if __name__ == '__main__':
    dns_server()
