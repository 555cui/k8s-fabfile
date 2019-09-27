# -*- coding:utf-8 -*-

PASSWORDS = {
    'host ip': {
        'user': 'ssh user',
        'port': 0,  # ssh port
        'password': 'ssh password'
    }
}

BASE_DIR = '/opt/kubernetes'

WORK_DIR = '/root/kubernetes'

# etcd
ETCD_HOSTS = ['etcd hosts']
ETCD_LISTEN_PEER_PORT = 2380
ETCD_LISTEN_CLIENT_PORT = 2379

# master
CLUSTER_IP = '100.100.0.0/16'
POD_IP = '10.168.0.0/16'

HA = False
FLOAT_IP = ''
MASTER_HOSTS = ['master hosts']
ADVICE_MASTER_PORT = 6443
BOOTSTRAP_TOKEN = 'abc123qwe456'
CNI = 'flannel'

# worker
WORKER_HOSTS = [
    'worker hosts'
]
PAUSE_IMAGE = 'library/pause-amd64:latest'
KUBE_ROUTER_IMAGE = 'library/kube-router:latest'
FLANNEL_IMAGE = 'library/flannel-amd64:latest'

# docker
DOCKER_ONLINE = True
