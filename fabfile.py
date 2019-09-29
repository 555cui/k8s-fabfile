# -*- coding:utf-8 -*-

from fabric.api import *
from setting import *
from utils import *

env.passwords = get_login_passwd()
env.roledefs = {
    'etcd': get_login_host(ETCD_HOSTS),
    'master': get_login_host(MASTER_HOSTS),
    'worker': get_login_host(WORKER_HOSTS)
}


def prepare():
    local('rm -rf ' + WORK_DIR + '/tmp')
    local('mkdir ' + WORK_DIR + '/tmp')
    local('mkdir -p ' + WORK_DIR + '/tmp/ssl/target')
    local('mkdir ' + WORK_DIR + '/tmp/kubeconfig')
    local('mkdir ' + WORK_DIR + '/tmp/yaml')
    local('cp -r ' + WORK_DIR + '/ssl/config ' + WORK_DIR + '/tmp/ssl/')


def ssl():
    # 设置api server列表
    master_hosts = ''
    for ip in MASTER_HOSTS:
        master_hosts += '"'
        master_hosts += ip
        master_hosts += '"'
        master_hosts += ','
    if HA:
        master_hosts += '"'
        master_hosts += FLOAT_IP
        master_hosts += '"'
        master_hosts += ','

    # 设置etcd server列表
    etcd_hosts = ''
    for ip in ETCD_HOSTS:
        etcd_hosts += '"'
        etcd_hosts += ip
        etcd_hosts += '"'
        etcd_hosts += ','

    cluster_ip = '"' + CLUSTER_IP[0] + '"'

    # 修改临时目录ssl证书配置，修改ip列表
    local('cp -r ' + WORK_DIR + '/ssl/config ' + WORK_DIR + '/tmp/ssl/config')

    api_file_path = WORK_DIR + '/tmp/ssl/config/apiserver-csr.json'
    etcd_file_path = WORK_DIR + '/tmp/ssl/config/etcd-csr.json'

    local(get_replace_format('__CLUSTER_API_IP__', cluster_ip, api_file_path))
    local(get_replace_format('__MASTER_HOSTS__', master_hosts, api_file_path))

    local(get_replace_format('__ETCD_HOSTS__', etcd_hosts, etcd_file_path))

    local('mkdir ' + WORK_DIR + '/tmp/ssl/target')

    # gen ca
    local(WORK_DIR + '/ssl/bin/cfssl gencert -initca ' +
          WORK_DIR + '/tmp/ssl/config/ca-csr.json | ' +
          WORK_DIR + '/ssl/bin/cfssljson -bare ' +
          WORK_DIR + '/tmp/ssl/target/ca')
    # gen etcd
    local(WORK_DIR + '/ssl/bin/cfssl gencert -ca=' +
          WORK_DIR + '/tmp/ssl/target/ca.pem -ca-key=' +
          WORK_DIR + '/tmp/ssl/target/ca-key.pem -config=' +
          WORK_DIR + '/tmp/ssl/config/ca-config.json -profile=kubernetes ' +
          WORK_DIR + '/tmp/ssl/config/etcd-csr.json | ' +
          WORK_DIR + '/ssl/bin/cfssljson -bare ' +
          WORK_DIR + '/tmp/ssl/target/etcd')
    # gen apiserver
    local(WORK_DIR + '/ssl/bin/cfssl gencert -ca=' +
          WORK_DIR + '/tmp/ssl/target/ca.pem -ca-key=' +
          WORK_DIR + '/tmp/ssl/target/ca-key.pem -config=' +
          WORK_DIR + '/tmp/ssl/config/ca-config.json -profile=kubernetes ' +
          WORK_DIR + '/tmp/ssl/config/apiserver-csr.json | ' +
          WORK_DIR + '/ssl/bin/cfssljson -bare ' +
          WORK_DIR + '/tmp/ssl/target/apiserver')
    # gen metrics
    local(WORK_DIR + '/ssl/bin/cfssl gencert -ca=' +
          WORK_DIR + '/tmp/ssl/target/ca.pem -ca-key=' +
          WORK_DIR + '/tmp/ssl/target/ca-key.pem -config=' +
          WORK_DIR + '/tmp/ssl/config/ca-config.json -profile=kubernetes ' +
          WORK_DIR + '/tmp/ssl/config/metrics-csr.json | ' +
          WORK_DIR + '/ssl/bin/cfssljson -bare ' +
          WORK_DIR + '/tmp/ssl/target/metrics')
    # gen kuberoute
    local(WORK_DIR + '/ssl/bin/cfssl gencert -ca=' +
          WORK_DIR + '/tmp/ssl/target/ca.pem -ca-key=' +
          WORK_DIR + '/tmp/ssl/target/ca-key.pem -config=' +
          WORK_DIR + '/tmp/ssl/config/ca-config.json -profile=kubernetes ' +
          WORK_DIR + '/tmp/ssl/config/kuberoute-csr.json | ' +
          WORK_DIR + '/ssl/bin/cfssljson -bare ' +
          WORK_DIR + '/tmp/ssl/target/kuberoute')
    # gen admin
    local(WORK_DIR + '/ssl/bin/cfssl gencert -ca=' +
          WORK_DIR + '/tmp/ssl/target/ca.pem -ca-key=' +
          WORK_DIR + '/tmp/ssl/target/ca-key.pem -config=' +
          WORK_DIR + '/tmp/ssl/config/ca-config.json -profile=kubernetes ' +
          WORK_DIR + '/tmp/ssl/config/admin-csr.json | ' +
          WORK_DIR + '/ssl/bin/cfssljson -bare ' +
          WORK_DIR + '/tmp/ssl/target/admin')
    # gen tiller
    local(WORK_DIR + '/ssl/bin/cfssl gencert -ca=' +
          WORK_DIR + '/tmp/ssl/target/ca.pem -ca-key=' +
          WORK_DIR + '/tmp/ssl/target/ca-key.pem -config=' +
          WORK_DIR + '/tmp/ssl/config/ca-config.json -profile=kubernetes ' +
          WORK_DIR + '/tmp/ssl/config/tiller-csr.json | ' +
          WORK_DIR + '/ssl/bin/cfssljson -bare ' +
          WORK_DIR + '/tmp/ssl/target/tiller')


def kubeconfig():
    local('cp -rf' + WORK_DIR + '/bin/kubectl /usr/local/bin/kubectl')
    local('chmod +x /usr/local/bin/kubectl')
    local('rm -rf ' + WORK_DIR + '/tmp/kubeconfig')
    local('mkdir -p ' + WORK_DIR + '/tmp/kubeconfig')
    if HA:
        master_ip = FLOAT_IP
    else:
        master_ip = MASTER_HOSTS[0]
    # gen bootstrap
    local('kubectl config set-cluster kubernetes'
          ' --certificate-authority=' + WORK_DIR + '/tmp/ssl/target/ca/ca.pem'
          ' --embed-certs=true'
          ' --server=https://' + master_ip + ':' + str(ADVICE_MASTER_PORT) +
          ' --kubeconfig=' + WORK_DIR + '/tmp/kubeconfig/bootstrap.kubeconfig')
    local('kubectl config set-credentials kubelet-bootstrap'
          ' --token=' + BOOTSTRAP_TOKEN +
          ' --kubeconfig=' + WORK_DIR + '/tmp/kubeconfig/bootstrap.kubeconfig')
    local('kubectl config set-context default'
          ' --cluster=kubernetes'
          ' --user=kubelet-bootstrap'
          ' --kubeconfig=' + WORK_DIR + '/tmp/kubeconfig/bootstrap.kubeconfig')
    local('kubectl config use-context default --kubeconfig=' + WORK_DIR + '/tmp/kubeconfig/bootstrap.kubeconfig')
    # gen kuberoute
    local('kubectl config set-cluster kubernetes --certificate-authority=' +
          WORK_DIR + '/tmp/ssl/target/ca.pem --embed-certs=true --server=https://' +
          master_ip + ':' + str(ADVICE_MASTER_PORT) +
          ' --kubeconfig=' + WORK_DIR + '/tmp/kubeconfig/kuberoute.kubeconfig')
    local('kubectl config set-credentials kube-router'
          ' --client-certificate=' + WORK_DIR + '/tmp/ssl/target/kuberoute.pem'
          ' --client-key=' + WORK_DIR + '/tmp/ssl/target/kuberoute-key.pem'
          ' --embed-certs=true'
          ' --kubeconfig=' + WORK_DIR + '/tmp/kubeconfig/kuberoute.kubeconfig')
    local('kubectl config set-context default'
          ' --cluster=kubernetes'
          ' --user=kube-router'
          ' --kubeconfig=' + WORK_DIR + '/tmp/kubeconfig/kuberoute.kubeconfig')
    local('kubectl config use-context default --kubeconfig=' + WORK_DIR + '/tmp/kubeconfig/kuberoute.kubeconfig')
    # gen admin
    local('kubectl config set-cluster kubernetes --certificate-authority=' +
          WORK_DIR + '/tmp/ssl/target/ca.pem --embed-certs=true --server=https://' +
          master_ip + ':' + str(ADVICE_MASTER_PORT))
    local('kubectl config set-credentials admin --client-certificate=' +
          WORK_DIR + '/tmp/ssl/target/admin.pem --embed-certs=true --client-key=' +
          WORK_DIR + '/tmp/ssl/target/admin-key.pem')
    local('kubectl config set-context kubernetes --cluster=kubernetes --user=admin')
    local('kubectl config use-context kubernetes')


def setting():
    local('kubectl apply -f ' + WORK_DIR + '/master/script/auto-csr-rbac.yaml')
    local('kubectl create clusterrolebinding kubelet-bootstrap'
          ' --clusterrole=system:node-bootstrapper --user=kubelet-bootstrap')
    local('kubectl create clusterrolebinding node-client-auto-approve-csr'
          ' --clusterrole=approve-node-client-csr --group=system:bootstrappers')
    local('kubectl create clusterrolebinding node-server-auto-renew-crt'
          ' --clusterrole=approve-node-server-renewal-csr --group=system:nodes')
    local('kubectl create clusterrolebinding node-client-auto-renew-crt'
          ' --clusterrole=approve-node-client-renewal-csr --group=system:nodes')
    local('kubectl create clusterrolebinding system-node-role-bound'
          ' --clusterrole=system:node --group=system:nodes')


@roles('etcd')
def etcd():
    # 分发软件包和证书
    run('mkdir -p ' + BASE_DIR + '/ssl')
    put(WORK_DIR + '/etcd', BASE_DIR + '/')
    put(WORK_DIR + '/tmp/ssl/target/etcd', BASE_DIR + '/ssl/')
    put(WORK_DIR + '/tmp/ssl/target/ca', BASE_DIR + '/ssl/')

    # ToDo 获取宿主机IP
    private_ip = env.host
    cluster_ip_list = ''
    for ip in ETCD_HOSTS:
        cluster_ip_list += ip
        cluster_ip_list += '=https://'
        cluster_ip_list += ip
        cluster_ip_list += ':'
        cluster_ip_list += str(ETCD_LISTEN_PEER_PORT)
        cluster_ip_list += ','
    cluster_ip_list = cluster_ip_list[:-1]

    etcd_listen_peer_urls = 'https://' + private_ip + ':' + str(ETCD_LISTEN_PEER_PORT)
    etcd_initial_advertise_peer_urls = 'https://' + private_ip + ":" + str(ETCD_LISTEN_PEER_PORT)
    etcd_listen_client_urls = 'https://' + private_ip + ":" + str(ETCD_LISTEN_CLIENT_PORT) \
                              + ',https://127.0.0.1:' + str(ETCD_LISTEN_CLIENT_PORT)
    etcd_advertise_client_urls = 'https://' + private_ip + ":" + str(ETCD_LISTEN_CLIENT_PORT)

    etcd_config_path = BASE_DIR + '/etcd/config/etcd.conf'
    etcd_service_path = BASE_DIR + '/etcd/service/etcd.service'

    run(get_replace_format('__BASE_DIR__', BASE_DIR, etcd_config_path))
    run(get_replace_format('__ETCD_NODE_NAME__', private_ip, etcd_config_path))
    run(get_replace_format('__ETCD_LISTEN_PEER_URLS__', etcd_listen_peer_urls, etcd_config_path))
    run(get_replace_format('__ETCD_INITIAL_ADVERTISE_PEER_URLS__', etcd_initial_advertise_peer_urls, etcd_config_path))
    run(get_replace_format('__ETCD_LISTEN_CLIENT_URLS__', etcd_listen_client_urls, etcd_config_path))
    run(get_replace_format('__ETCD_ADVERTISE_CLIENT_URLS__', etcd_advertise_client_urls, etcd_config_path))
    run(get_replace_format('__ETCD_INITIAL_CLUSTER__', cluster_ip_list, etcd_config_path))
    run(get_replace_format('__BASE_DIR__', BASE_DIR, etcd_service_path))

    run('chmod +x ' + BASE_DIR + '/etcd/bin/etcd')
    run('cp -rf ' + BASE_DIR + '/etcd/service/etcd.service /usr/bin/systemd/system/etcd.service')
    run('systemctl daemon-reload')
    run('systemctl restart etcd')
    run('systemctl enabled etcd')


@roles('master')
def master():
    # 分发软件包和证书
    run('mkdir -p ' + BASE_DIR + '/ssl')
    put(WORK_DIR + '/master', BASE_DIR + '/')
    put(WORK_DIR + '/tmp/ssl/etcd', BASE_DIR + '/ssl/')
    put(WORK_DIR + '/tmp/ssl/apiserver', BASE_DIR + '/ssl/')
    put(WORK_DIR + '/tmp/ssl/metrics', BASE_DIR + '/ssl/')
    put(WORK_DIR + '/tmp/ssl/ca', BASE_DIR + '/ssl/')

    etcd_servers = ''
    for ip in ETCD_HOSTS:
        etcd_servers += 'https://'
        etcd_servers += ip
        etcd_servers += ':'
        etcd_servers += str(ETCD_LISTEN_CLIENT_PORT)
        etcd_servers += ','
    etcd_servers = etcd_servers[:-1]

    # ToDo 获取私网IP
    private_ip = env.host

    run("sed -i 's#__TOKEN__#" + BOOTSTRAP_TOKEN + "#g' " + BASE_DIR + "/master/token/token.csv")
    run("sed -i 's#__ETCD_SERVERS__#" + etcd_servers + "#g' " + BASE_DIR + "/master/config/kube-apiserver.cfg")
    run("sed -i 's#__BIND_ADDRESS__#" + private_ip + "#g' " + BASE_DIR + "/master/config/kube-apiserver.cfg")
    run("sed -i 's#__ADVERTISE_ADDRESS__#" + private_ip + "#g' " + BASE_DIR + "/master/config/kube-apiserver.cfg")
    run("sed -i 's#__SECURE_PORT__#" + str(ADVICE_MASTER_PORT) + "#g' " + BASE_DIR + "/master/config/kube-apiserver.cfg")
    run(
        "sed -i 's#__SERVICE_CLUSTER_IP_RANGE__#" + CLUSTER_IP + "#g' " + BASE_DIR + "/master/config/kube-apiserver.cfg")
    run('sed -i "s#__BASE_DIR__#' + BASE_DIR + '#g" ' + BASE_DIR + '/master/config/kube-apiserver.cfg')

    run(
        "sed -i 's#__SERVICE_CLUSTER_IP_RANGE__#" + CLUSTER_IP + "#g' " + BASE_DIR + "/master/config/kube-controller-manager.cfg")
    run("sed -i 's#__CLUSTER_CIDR__#" + POD_IP + "#g' " + BASE_DIR + "/master/config/kube-controller-manager.cfg")
    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + BASE_DIR + "/master/config/kube-controller-manager.cfg")

    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + BASE_DIR + "/master/service/kube-apiserver.service")
    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + BASE_DIR + "/master/service/kube-controller-manager.service")
    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + BASE_DIR + "/master/service/kube-scheduler.service")

    run("sh " + BASE_DIR + "/master/script/init.sh " + BASE_DIR)


@roles('worker')
def worker():
    # 分发软件包和配置
    run('mkdir /opt/cni')
    run('mkdir /etc/cni')

    put(WORK_DIR + '/cni/bin', '/opt/cni/')
    put(WORK_DIR + '/cni/net.d', '/etc/cni/')
    put(WORK_DIR + '/worker', BASE_DIR + '/')
    run('mkdir ' + BASE_DIR + '/worker/kubeconfig')
    put(WORK_DIR + '/tmp/kubeconfig/bootstrap.kubeconfig', BASE_DIR + '/worker/kubeconfig/bootstrap.kubeconfig')
    # ToDo 获取私网IP
    private_ip = env.host

    run('chmod +x /opt/cni/bin/*')
    run("sed -i 's#__HOSTNAME_OVERRIDE__#" + private_ip + "#g' " + BASE_DIR + "/worker/config/kubelet.conf")

    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + BASE_DIR + "/worker/service/kubelet.service")
    run("cp -rf" + BASE_DIR + "/worker/service/kubelet.service /usr/bin/systemd/system/kubelet.service")
    run("systemctl daemon-reload")
    run("systemctl restart kubelet")
    run('systemctl enable kubelet')


def proxy():
    if HA:
        master_ip = 'https://' + FLOAT_IP + ':' + str(ADVICE_MASTER_PORT)
    else:
        master_ip = 'https://' + MASTER_HOSTS[0] + ':' + str(ADVICE_MASTER_PORT)

    local('kubectl create configmap'
          ' -n kube-system kuberoute-kubeconfig'
          ' --from-file=' + WORK_DIR + '/tmp/kubeconfig/kuberoute.kubeconfig')
    local('kubectl apply -f ' + WORK_DIR + '/master/plugin/kube-router/kuberoute.yaml')


def network():
    if CNI == 'flannel':
        local('kubectl apply -f ' + WORK_DIR + '/master/plugin/flannel')


def core_dns():
    local('cp ' + WORK_DIR + '/master/plugin/coredns/coredns.yaml ' + WORK_DIR + '/tmp/yaml/')
    local('sed -i "s#__CLUSTER_DNS_IP__#' + CLUSTER_IP[1] + '#g" ' + WORK_DIR + '/tmp/yaml/coredns.yaml')
    local('kubectl apply -f ' + WORK_DIR + '/tmp/yaml/coredns.yaml')

