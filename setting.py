# -*- coding:utf-8 -*-

BASE_DIR = '/opt/kubernetes'
LOCAL_DIR = '/root/kubernetes'
TMP_DIR = '~/tmp'

HOST_USER = 'root'
HOST_PASSWORD = 'LH@21cn.com'
PRIVATE_NETWORK_CARD = 'eth0'

# etcd
ETCD_HOSTS = ['10.61.66.206']
ETCD_LISTEN_PEER_PORT = 2380
ETCD_LISTEN_CLIENT_PORT = 2379

# master
CLUSTER_IP = '172.18.0.0/16'
CLUSTER_API_IP = '172.18.0.1'
CLUSTER_DNS_IP = '172.18.0.2'
POD_IP = '192.168.0.0/16'

HA = False
FLOAT_IP = ''
MASTER_HOSTS = ['10.61.66.206']
ADVICE_MASTER_PORT = 6443
BOOTSTRAP_TOKEN = ''
CNI = 'flannel'

# worker
WORKER_HOSTS = ['10.61.66.206']
PAUSE_IMAGE = 'mec-hub.21cn.com/library/pause-amd64:latest'
KUBE_ROUTER_IMAGE = 'mec-hub.21cn.com/library/kube-router:latest'
FLANNEL_IMAGE = 'mec-hub.21cn.com/library/flannel-amd64:latest'

# docker
DOCKER_ONLINE = True