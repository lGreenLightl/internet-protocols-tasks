from urllib.request import Request, urlopen
import json
import argparse


def get_person_friends(user_id, token, version):
    if not user_id.isdigit():
        try:
            user_id = get_user_name_id(user_id, token, version)
        except KeyError:
            raise ValueError("User doesn't exist!")

    person_friends = (f'https://api.vk.com/method/friends.get?user_id={user_id}'
                      f'&order=name&fields=nickname,domain'
                      f'&access_token={token}'
                      f'&v={version}')
    try:
        return api_request(person_friends)['response']
    except KeyError:
        raise KeyError(f"{api_request(person_friends)['error']['error_msg']}")


def get_user_name_id(name, token, version):
    name_id = (f'https://api.vk.com/method/users.get?user_id={name}'
               f'&access_token={token}'
               f'&v={version}')
    return api_request(name_id)['response'][0]['id']


def api_request(request_message):
    return json.loads(urlopen(Request(request_message)).read())


def start_app():
    parser = argparse.ArgumentParser()
    parser.add_argument('--userid', required=True, help='user id')
    parser.add_argument('--token', required=True, help='your token')
    args_parser = parser.parse_args()
    api_response = get_person_friends(args_parser.userid, args_parser.token, '5.131')['items']
    with open('../resources-8/response.txt', 'w', encoding='utf-8') as file:
        file.write('\n'.join([f"{person['first_name']} {person['last_name']}" for person in api_response]))


if __name__ == '__main__':
    start_app()
