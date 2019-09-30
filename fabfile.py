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
    local('mkdir ' + WORK_DIR + '/tmp/ssl')
    local('mkdir ' + WORK_DIR + '/tmp/kubeconfig')
    local('mkdir ' + WORK_DIR + '/tmp/yaml')
    local('cp -r ' + WORK_DIR + '/ssl/config ' + WORK_DIR + '/tmp/ssl/')

    local('chmod +x ' + WORK_DIR + '/ssl/bin/*')


def ssl():
    local('rm -rf ' + WORK_DIR + '/tmp/ssl/target')
    local('mkdir ' + WORK_DIR + '/tmp/ssl/target')
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

    cluster_ip = '"' + str(CLUSTER_IP[1]) + '"'

    # 修改临时目录ssl证书配置，修改ip列表
    gen_setting_path = WORK_DIR + '/tmp/ssl/config/ca-config.json'
    api_file_path = WORK_DIR + '/tmp/ssl/config/apiserver-csr.json'
    etcd_file_path = WORK_DIR + '/tmp/ssl/config/etcd-csr.json'

    local(get_replace_format('__EXPIRY__', SSL_EXPIRY, gen_setting_path))
    local(get_replace_format('__CLUSTER_API_IP__', cluster_ip, api_file_path))
    local(get_replace_format('__MASTER_HOSTS__', master_hosts, api_file_path))

    local(get_replace_format('__ETCD_HOSTS__', etcd_hosts, etcd_file_path))

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
    local('cp -rf ' + WORK_DIR + '/bin/kubectl /usr/local/bin/kubectl')
    local('chmod +x /usr/local/bin/kubectl')
    local('rm -rf ' + WORK_DIR + '/tmp/kubeconfig')
    local('mkdir -p ' + WORK_DIR + '/tmp/kubeconfig')
    if HA:
        master_ip = FLOAT_IP
    else:
        master_ip = MASTER_HOSTS[0]
    # gen bootstrap
    local('kubectl config set-cluster kubernetes'
          ' --certificate-authority=' + WORK_DIR + '/tmp/ssl/target/ca.pem'
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


@roles('etcd')
def etcd():
    put(WORK_DIR + '/bin/etcdctl', '/usr/local/bin/')
    run('chmod +x /usr/local/bin/etcdctl')
    # 分发软件包和证书
    run('rm -rf ' + BASE_DIR + '/etcd')
    run('mkdir -p ' + BASE_DIR + '/etcd')
    run('mkdir -p ' + BASE_DIR + '/etcd/ssl')
    run('mkdir -p ' + BASE_DIR + '/etcd/bin')
    run('mkdir -p ' + BASE_DIR + '/etcd/conf')
    put(WORK_DIR + '/bin/etcd', BASE_DIR + '/etcd/bin/')
    put(WORK_DIR + '/conf/etcd.cfg', BASE_DIR + '/etcd/conf/')
    put(WORK_DIR + '/service/etcd.service', '/usr/lib/systemd/system/')
    put(WORK_DIR + '/tmp/ssl/target/etcd*', BASE_DIR + '/etcd/ssl/')
    put(WORK_DIR + '/tmp/ssl/target/ca*', BASE_DIR + '/etcd/ssl/')
    run('chmod +x ' + BASE_DIR + '/etcd/bin/*')

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

    etcd_config_path = BASE_DIR + '/etcd/conf/etcd.cfg'
    etcd_service_path = '/usr/lib/systemd/system/etcd.service'

    run(get_replace_format('__BASE_DIR__', BASE_DIR, etcd_config_path))
    run(get_replace_format('__ETCD_NODE_NAME__', private_ip, etcd_config_path))
    run(get_replace_format('__ETCD_LISTEN_PEER_URLS__', etcd_listen_peer_urls, etcd_config_path))
    run(get_replace_format('__ETCD_INITIAL_ADVERTISE_PEER_URLS__', etcd_initial_advertise_peer_urls, etcd_config_path))
    run(get_replace_format('__ETCD_LISTEN_CLIENT_URLS__', etcd_listen_client_urls, etcd_config_path))
    run(get_replace_format('__ETCD_ADVERTISE_CLIENT_URLS__', etcd_advertise_client_urls, etcd_config_path))
    run(get_replace_format('__ETCD_INITIAL_CLUSTER__', cluster_ip_list, etcd_config_path))
    run(get_replace_format('__BASE_DIR__', BASE_DIR, etcd_service_path))

    run('systemctl daemon-reload')
    run('systemctl restart etcd')
    run('systemctl enable etcd')


@roles('master')
def master():
    # 创建目录
    run('rm -rf ' + BASE_DIR + '/master')
    run('mkdir -p ' + BASE_DIR + '/master')
    run('mkdir -p ' + BASE_DIR + '/master/ssl')
    run('mkdir -p ' + BASE_DIR + '/master/bin')
    run('mkdir -p ' + BASE_DIR + '/master/conf')
    run('mkdir -p ' + BASE_DIR + '/master/token')

    put(WORK_DIR + '/tmp/ssl/target/etcd*', BASE_DIR + '/master/ssl/')
    put(WORK_DIR + '/tmp/ssl/target/apiserver*', BASE_DIR + '/master/ssl/')
    put(WORK_DIR + '/tmp/ssl/target/metrics*', BASE_DIR + '/master/ssl/')
    put(WORK_DIR + '/tmp/ssl/target/ca*', BASE_DIR + '/master/ssl/')

    put(WORK_DIR + '/conf/kube-apiserver.cfg', BASE_DIR + '/master/conf/')
    put(WORK_DIR + '/conf/kube-controller-manager.cfg', BASE_DIR + '/master/conf/')
    put(WORK_DIR + '/conf/kube-scheduler.cfg', BASE_DIR + '/master/conf/')
    put(WORK_DIR + '/token/token.csv', BASE_DIR + '/master/token/')

    put(WORK_DIR + '/service/kube-apiserver.service', '/usr/lib/systemd/system/')
    put(WORK_DIR + '/service/kube-controller-manager.service', '/usr/lib/systemd/system/')
    put(WORK_DIR + '/service/kube-scheduler.service', '/usr/lib/systemd/system/')

    # 分发软件包和证书
    put(WORK_DIR + '/bin/kube-apiserver', BASE_DIR + '/master/bin/')
    put(WORK_DIR + '/bin/kube-controller-manager', BASE_DIR + '/master/bin/')
    put(WORK_DIR + '/bin/kube-scheduler', BASE_DIR + '/master/bin/')

    etcd_servers = ''
    for ip in ETCD_HOSTS:
        etcd_servers += 'https://'
        etcd_servers += ip
        etcd_servers += ':'
        etcd_servers += str(ETCD_LISTEN_CLIENT_PORT)
        etcd_servers += ','
    etcd_servers = etcd_servers[:-1]

    private_ip = env.host

    run("sed -i 's#__TOKEN__#" + BOOTSTRAP_TOKEN + "#g' " + BASE_DIR + "/master/token/token.csv")
    run("sed -i 's#__ETCD_SERVERS__#" + etcd_servers + "#g' " + BASE_DIR + "/master/conf/kube-apiserver.cfg")
    run("sed -i 's#__BIND_ADDRESS__#" + private_ip + "#g' " + BASE_DIR + "/master/conf/kube-apiserver.cfg")
    run("sed -i 's#__ADVERTISE_ADDRESS__#" + private_ip + "#g' " + BASE_DIR + "/master/conf/kube-apiserver.cfg")
    run("sed -i 's#__SECURE_PORT__#" + str(ADVICE_MASTER_PORT) + "#g' " + BASE_DIR + "/master/conf/kube-apiserver.cfg")
    run("sed -i 's#__SERVICE_CLUSTER_IP_RANGE__#" + str(CLUSTER_IP) + "#g' " + BASE_DIR + "/master/conf/kube-apiserver.cfg")
    run('sed -i "s#__BASE_DIR__#' + BASE_DIR + '#g" ' + BASE_DIR + '/master/conf/kube-apiserver.cfg')

    run("sed -i 's#__SERVICE_CLUSTER_IP_RANGE__#" + str(CLUSTER_IP) + "#g' " + BASE_DIR + "/master/conf/kube-controller-manager.cfg")
    run("sed -i 's#__CLUSTER_CIDR__#" + POD_IP + "#g' " + BASE_DIR + "/master/conf/kube-controller-manager.cfg")
    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + BASE_DIR + "/master/conf/kube-controller-manager.cfg")

    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + "/usr/lib/systemd/system/kube-apiserver.service")
    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + "/usr/lib/systemd/system/kube-controller-manager.service")
    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + "/usr/lib/systemd/system/kube-scheduler.service")

    run('chmod +x ' + BASE_DIR + '/master/bin/*')
    run('systemctl daemon-reload')
    run('systemctl start kube-apiserver')
    run('systemctl start kube-controller-manager')
    run('systemctl start kube-scheduler')

    # ToDo HA


def setting():
    local('kubectl apply -f ' + WORK_DIR + '/yaml/setting/auto-csr-rbac.yaml')


# docker安装
@roles('worker')
def docker():
    put(WORK_DIR + '/docker/conf/ipv4.conf', '/etc/sysctl.d/')
    run('setenforce 0')
    run('sed -i "s/^SELINUX=enforcing/SELINUX=disabled/g" /etc/sysconfig/selinux')
    run('sed -i "s/^SELINUX=enforcing/SELINUX=disabled/g" /etc/selinux/config')
    run('sed -i "s/^SELINUX=permissive/SELINUX=disabled/g" /etc/sysconfig/selinux')
    run('sed -i "s/^SELINUX=permissive/SELINUX=disabled/g" /etc/selinux/config')
    run('getenforce')
    run('swapoff -a')
    run("sed -i 's/.*swap.*/#&/' /etc/fstab")
    run('modprobe br_netfilter')
    run('sysctl -p /etc/sysctl.d/k8s.conf')
    if DOCKER_ONLINE:
        pass
    else:
        put(WORK_DIR + '/docker/package/' + DOCKER_PACKAGE, '/tmp/')
        put(WORK_DIR + '/docker/service/docker.service', '/usr/lib/systemd/system/')
        run('tar -zxvf /tmp/' + DOCKER_PACKAGE + ' -C /tmp/')
        run('chmod +x /tmp/docker/*')
        run('mv /tmp/docker/* /usr/bin/')
        run('rm -rf /tmp/docker')
        run('rm -rf /tmp/' + DOCKER_PACKAGE)
        run('systemctl daemon-reload')
        run('systemctl start docker')
        run('systemctl enable docker')


@roles('worker')
def worker():
    # 分发软件包和配置
    run('rm -rf /opt/cni')
    run('rm -rf /etc/cni')
    run('rm -rf ' + BASE_DIR + '/worker')
    run('mkdir /opt/cni')
    run('mkdir /etc/cni')
    run('mkdir -p ' + BASE_DIR + '/worker')
    run('mkdir ' + BASE_DIR + '/worker/bin')
    run('mkdir ' + BASE_DIR + '/worker/conf')
    run('mkdir ' + BASE_DIR + '/worker/log')
    run('mkdir ' + BASE_DIR + '/worker/kubeconfig')

    put(WORK_DIR + '/cni/bin', '/opt/cni/')
    put(WORK_DIR + '/cni/net.d', '/etc/cni/')
    put(WORK_DIR + '/bin/kubelet', BASE_DIR + '/worker/bin/')
    put(WORK_DIR + '/conf/kubelet.cfg', BASE_DIR + '/worker/conf/')
    put(WORK_DIR + '/tmp/kubeconfig/bootstrap.kubeconfig', BASE_DIR + '/worker/kubeconfig/bootstrap.kubeconfig')
    put(WORK_DIR + '/service/kubelet.service', '/usr/lib/systemd/system/')

    private_ip = env.host

    run("sed -i 's#__HOSTNAME_OVERRIDE__#" + private_ip + "#g' " + BASE_DIR + "/worker/conf/kubelet.cfg")
    run("sed -i 's#__CLUSTER_DNS__#" + str(CLUSTER_IP[2]) + "#g' " + BASE_DIR + "/worker/conf/kubelet.cfg")
    run("sed -i 's#__PAUSE_IMAGE__#" + PAUSE_IMAGE + "#g' " + BASE_DIR + "/worker/conf/kubelet.cfg")
    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + BASE_DIR + "/worker/conf/kubelet.cfg")
    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + "/usr/lib/systemd/system/kubelet.service")

    run('chmod +x /opt/cni/bin/*')
    run('chmod +x ' + BASE_DIR + '/worker/bin/*')
    run('systemctl daemon-reload')
    run('systemctl start kubelet')
    run('systemctl enable kubelet')


def proxy():
    local('cp ' + WORK_DIR + '/yaml/kube-router ' + WORK_DIR + '/tmp/yaml/')
    local("sed -i 's#__KUBE_ROUTER_IMAGE__#" + KUBE_ROUTER_IMAGE + "#g' " + WORK_DIR + "/tmp/yaml/kube-router/kuberoute.yaml")

    local('kubectl create configmap'
          ' -n kube-system kuberoute-kubeconfig'
          ' --from-file=' + WORK_DIR + '/tmp/kubeconfig/kuberoute.kubeconfig')
    local('kubectl apply -f ' + WORK_DIR + '/yaml/kube-router')


def network():
    if CNI == 'flannel':
        local('cp ' + WORK_DIR + '/yaml/flannel ' + WORK_DIR + '/tmp/yaml/')
        local("sed -i 's#__POD_IP__#" + POD_IP + "#g' " + WORK_DIR + "/tmp/yaml/flannel/kube-flannel-legacy.yaml")
        local("sed -i 's#__FLANNEL_IMAGE__#" + FLANNEL_IMAGE + "#g' " + WORK_DIR + "/tmp/yaml/flannel/kube-flannel-legacy.yaml")
        local('kubectl apply -f ' + WORK_DIR + '/tmp/yaml/flannel')


def core_dns():
    local('cp ' + WORK_DIR + '/yaml/coredns ' + WORK_DIR + '/tmp/yaml/')
    local('sed -i "s#__CLUSTER_DNS_IP__#' + CLUSTER_IP[2] + '#g" ' + WORK_DIR + '/tmp/yaml/coredns/coredns.yaml')
    local('kubectl apply -f ' + WORK_DIR + '/tmp/yaml/coredns')

