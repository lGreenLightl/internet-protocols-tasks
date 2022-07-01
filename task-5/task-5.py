from argparse import ArgumentParser
from json import loads
from re import compile
from subprocess import PIPE, Popen, STDOUT
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ip_reg = compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
as_reg = compile(r'"origin": "(\d+?)",')


def get_additional_information(ip):
    country, provider = '--', '--'
    url = f'https://stat.ripe.net/data/whois/data.json?resource={ip}'

    try:
        with urlopen(url) as page:
            data = loads(page.read().decode('utf-8'))['data']
    except (URLError, HTTPError):
        return country, provider

    country, provider = process_records(data, 'records')

    if '--' in (country, provider):
        result = process_records(data, 'irr_records')
        provider = result[1] if result[1] != '--' else provider
        country = result[0] if result[0] != '--' else country

    return country, provider


def get_as_number(ip):
    url = f'https://stat.ripe.net/data/routing-status/data.json?resource={ip}'

    try:
        with urlopen(url) as page:
            return f'AS{as_reg.findall(page.read().decode())[0]}'
    except IndexError:
        return None
    except (HTTPError, URLError) as err:
        return str(err)


def main(ip_address):
    traceroute = Popen(['tracert', ip_address],
                       stdout=PIPE,
                       stderr=STDOUT)
    ip_number = 1
    flag = False
    last_ip = None

    for line in iter(traceroute.stdout.readline, ""):
        line = line.decode(encoding='cp866')
        if line.find('Не удается разрешить системное имя узла') != -1:
            break
        elif line.find('Трассировка маршрута') != -1:
            last_ip = ip_reg.findall(line)[0]
        elif line.find('с максимальным числом прыжков') != -1:
            print('№' +
                  ' ' * 4 +
                  'IP' +
                  ' ' * 16 +
                  'AS' +
                  ' ' * 7 +
                  'Country' +
                  ' ' * 3 +
                  'Provider')
            flag = True

        try:
            ip = ip_reg.findall(line)[0]
        except IndexError:
            continue

        if flag:
            as_number = get_as_number(ip)
            country, provider = (get_additional_information(ip)
                                 if as_number is not None else ('--', '--'))

            if as_number is None:
                as_number = '--'

            string_ip = ip + (' ' * (15 - len(ip))) if len(ip) < 15 else ip
            print(table_raw_to_str(str(ip_number), string_ip,
                                   as_number, country,
                                   provider))
            ip_number += 1
            if ip == last_ip:
                break


def process_records(records, records_key):
    country, provider = '--', '--'

    for record in records[records_key]:
        if provider != '--' and country != '--':
            break
        for element in record:
            if provider != '--' and country != '--':
                break
            if country == '--' and element['key'].lower() == 'country':
                country = element['value']
            if provider == '--' and element['key'].lower() == 'descr':
                provider = element['value']

    return country, provider


def table_raw_to_str(ip_number, current_ip, as_number, country, provider):
    return (ip_number +
            ' ' * (5 - len(ip_number)) +
            current_ip + ' ' * (18 - len(current_ip)) +
            as_number +
            ' ' * (9 - len(as_number)) +
            country +
            ' ' * (10 - len(country)) +
            provider)


if __name__ == '__main__':
    arg_parser = ArgumentParser()
    arg_parser.add_argument('-d', '--destination', dest='dest', required=True)
    arg = arg_parser.parse_args()
    main(arg.dest)
