# -*- coding:utf-8 -*-

PASSWORDS = {
    'host ip': {
        'user': 'ssh user',
        'port': 0,  # ssh port
        'password': 'ssh password'
    }
    # ...
}

BASE_DIR = '/opt/kubernetes'
WORK_DIR = '/root/kubernetes'

# ssl
SSL_EXPIRY = '87600h'

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

PAUSE_IMAGE = 'registry.cn-hangzhou.aliyuncs.com/google-containers/pause-amd64:3.0'
KUBE_ROUTER_IMAGE = 'cloudnativelabs/kube-router'
FLANNEL_IMAGE = 'library/flannel:v0.10.0-amd64'
CORE_DNS_IMAGE = 'coredns/coredns'
METRICS_IMAGE = 'library/metrics:latest'
TILLER_IMAGE = 'library/tiller:v2.14.3'

# docker
DOCKER_ONLINE = False
DOCKER_PACKAGE = 'docker-19.03.2.tgz'
