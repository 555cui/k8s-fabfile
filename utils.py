from setting import PASSWORDS, CLUSTER_IP
from IPy import IP

CLUSTER_IP = IP(CLUSTER_IP)

__replace_format__ = 'sed -i \'s#{source}#{target}#g\' {file}'


def get_login_host(hosts):
    result = []
    for host in hosts:
        result.append(PASSWORDS[host]['user'] + '@' + host + ':' + str(PASSWORDS[host]['port']))
    return result


def get_login_passwd():
    result = {}
    for host in PASSWORDS:
        result[PASSWORDS[host]['user'] + '@' + host + ':' + PASSWORDS[host]['port']] = PASSWORDS[host]['password']
    return result


def get_replace_format(source, target, file):
    return __replace_format__.format(source=source, target=target, file=file)