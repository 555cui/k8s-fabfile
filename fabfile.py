# -*- coding:utf-8 -*-

from fabric.api import *
from setting import *

env.user = HOST_USER
env.password = HOST_PASSWORD
env.roledefs = {
    'etcd': ETCD_HOSTS,
    'master': MASTER_HOSTS,
    'worker': WORKER_HOSTS
}


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

    cluster_ip = '"' + CLUSTER_API_IP + '"'

    # 修改临时目录ssl证书配置，修改ip列表
    local('mkdir ' + TMP_DIR)
    local('cp -r ' + LOCAL_DIR + '/ssl ' + TMP_DIR + '/')
    local("sed -i 's/__CLUSTER_API_IP__/" + cluster_ip + "/g' " + TMP_DIR + "/ssl/config/apiserver-csr.json")
    local("sed -i 's/__MASTER_HOSTS__/" + master_hosts + "/g' " + TMP_DIR + "/ssl/config/apiserver-csr.json")
    local("sed -i 's/__ETCD_HOSTS__/" + etcd_hosts + "/g' " + TMP_DIR + "/ssl/config/etcd-csr.json")
    local("sh " + TMP_DIR + "/ssl/script/init.sh " + TMP_DIR)


@roles('etcd')
def etcd():
    # 分发软件包和证书
    run('mkdir -p ' + BASE_DIR + '/ssl')
    put(LOCAL_DIR + '/etcd', BASE_DIR + '/')
    put(TMP_DIR + '/ssl/etcd', BASE_DIR + '/ssl/')
    put(TMP_DIR + '/ssl/ca', BASE_DIR + '/ssl/')

    # ToDo 获取宿主机IP
    private_ip = run("ifconfig " + PRIVATE_NETWORK_CARD + " | grep 'inet ' | awk '{print $2}'")
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

    run('sed -i "s#__BASE_DIR__#' + BASE_DIR + '#g" ' + BASE_DIR + "/etcd/config/etcd.conf")
    run("sed -i 's#__ETCD_NODE_NAME__#" + private_ip + "#g' " + BASE_DIR + "/etcd/config/etcd.conf")
    run("sed -i 's#__ETCD_LISTEN_PEER_URLS__#" + etcd_listen_peer_urls + "#g' " + BASE_DIR + "/etcd/config/etcd.conf")
    run(
        "sed -i 's#__ETCD_INITIAL_ADVERTISE_PEER_URLS__#" + etcd_initial_advertise_peer_urls + "#g' " + BASE_DIR + "/etcd/config/etcd.conf")
    run(
        "sed -i 's#__ETCD_LISTEN_CLIENT_URLS__#" + etcd_listen_client_urls + "#g' " + BASE_DIR + "/etcd/config/etcd.conf")
    run(
        "sed -i 's#__ETCD_ADVERTISE_CLIENT_URLS__#" + etcd_advertise_client_urls + "#g' " + BASE_DIR + "/etcd/config/etcd.conf")
    run("sed -i 's#__ETCD_INITIAL_CLUSTER__#" + cluster_ip_list + "#g' " + BASE_DIR + "/etcd/config/etcd.conf")
    run("sed -i 's#__BASE_DIR__#" + BASE_DIR + "#g' " + BASE_DIR + "/etcd/service/etcd.service")
    run("sh " + BASE_DIR + "/etcd/script/init.sh " + BASE_DIR)


@roles('master')
def master():
    # 分发软件包和证书
    run('mkdir -p' + BASE_DIR + '/ssl')
    put(LOCAL_DIR + '/master', BASE_DIR + '/')
    put(TMP_DIR + '/ssl/etcd', BASE_DIR + '/ssl/')
    put(TMP_DIR + '/ssl/apiserver', BASE_DIR + '/ssl/')
    put(TMP_DIR + '/ssl/metrics', BASE_DIR + '/ssl/')
    put(TMP_DIR + '/ssl/ca', BASE_DIR + '/ssl/')

    etcd_servers = ''
    for ip in ETCD_HOSTS:
        etcd_servers += 'https://'
        etcd_servers += ip
        etcd_servers += ':'
        etcd_servers += str(ETCD_LISTEN_CLIENT_PORT)
        etcd_servers += ','
    etcd_servers = etcd_servers[:-1]

    # ToDo 获取私网IP
    private_ip = run("ifconfig " + PRIVATE_NETWORK_CARD + " | grep 'inet ' | awk '{print $2}'")

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
def docker():
    # prepare
    run('setenforce 0')
    run('sed -i "s#^SELINUX=enforcing#SELINUX=disabled#g" /etc/sysconfig/selinux')
    run('sed -i "s#^SELINUX=enforcing#SELINUX=disabled#g" /etc/selinux/config')
    run('sed -i "s#^SELINUX=permissive#SELINUX=disabled#g" /etc/sysconfig/selinux')
    run('sed -i "s#^SELINUX=permissive#SELINUX=disabled#g" /etc/selinux/config')
    run('swapoff -a')
    run('sed -i "s/.*sway.*/#&/" /etc/fstab')
    run('cat <<EOF > /etc/sysctl.d/k8s.conf\n'
        'net.ipv4.ip_forward=1\n'
        'net.bridge.bridge-nf-call-ip6tables=1\n'
        'net.bridge.bridge-nf-call-iptables=1\n'
        'EOF')
    run('modprobe br_netfilter')
    run('sysctl -p /etc/sysctl.d/k8s.conf')
    # 分发软件包和配置
    if DOCKER_ONLINE:
        run('yum install -y yum-utils device-mapper-persistent-data lvm2')
        run('yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo')
        run('yum install -y docker-ce')
    else:
        run('rm -rf ' + TMP_DIR)
        run('mkdir -p ' + TMP_DIR)
        put(LOCAL_DIR + '/docker/package', TMP_DIR + '/')
        # 离线安装docker
        run("rpm -ivh " + TMP_DIR + "/package/libtool-ltdl-2.4.2-22.el7_3.x86_64.rpm")
        run("rpm -ivh " + TMP_DIR + "/package/containerd.io-1.2.0-3.el7.x86_64.rpm")
        run("rpm -ivh " + TMP_DIR + "/package/docker-ce-18.09.0-3.el7.x86_64.rpm")
        run("rpm -ivh " + TMP_DIR + "/package/container-selinux-2.66-1.el7.noarch.rpm")
        run("rpm -ivh " + TMP_DIR + "/package/docker-ce-18.09.0-3.el7.x86_64.rpm")

    # 覆盖docker配置文件
    run("mkdir -p /etc/docker")
    put(LOCAL_DIR + '/docker/daemon.json', '/etc/docker/')

    # 启动docker
    run("systemctl start docker")
    run("systemctl enable docker")


@roles('worker')
def worker():
    if HA:
        master_ip = FLOAT_IP
    else:
        master_ip = MASTER_HOSTS[0]
    local('kubectl config set-cluster kubernetes'
          ' --certificate-authority=' + TMP_DIR + '/ssl/ca/ca.pem'
          ' --embed-certs=true'
          ' --server=https://' + master_ip + ':' + str(ADVICE_MASTER_PORT) +
          ' --kubeconfig=' + TMP_DIR + '/kubeconfig/bootstrap.kubeconfig')
    local('kubectl config set-credentials kubelet-bootstrap'
          ' --token=' + BOOTSTRAP_TOKEN +
          ' --kubeconfig=' + TMP_DIR + '/kubeconfig/bootstrap.kubeconfig')
    local('kubectl config set-context default'
          ' --cluster=kubernetes'
          ' --user=kubelet-bootstrap'
          ' --kubeconfig=' + TMP_DIR + '/kubeconfig/bootstrap.kubeconfig')
    local('kubectl config use-context default --kubeconfig=' + TMP_DIR + '/kubeconfig/bootstrap.kubeconfig')

    # 分发软件包和配置
    put(LOCAL_DIR + '/worker', BASE_DIR + '/')
    run('mkdir /opt/cni')
    put(LOCAL_DIR + '/cni/bin', '/opt/cni/')
    put(TMP_DIR + '/kubeconfig', BASE_DIR + '/worker/')
    # ToDo 获取私网IP
    private_ip = run("ifconfig " + PRIVATE_NETWORK_CARD + " | grep 'inet ' | awk '{print $2}'")

    run('chmod +x /opt/cni/bin/*')
    run("sed -i 's/__HOSTNAME_OVERRIDE__/" + private_ip + "/g' " + BASE_DIR + "/worker/config/kubelet.conf")
    run('mkdir /etc/cni')
    put(LOCAL_DIR + '/cni/net.d', '/etc/cni/')

    run("sed -i 's/__BASE_DIR__/" + BASE_DIR + "/g' " + BASE_DIR + "/worker/service/kubelet.service")
    run("cp " + BASE_DIR + "/worker/service/kubelet.service /usr/bin/systemd/system/kubelet.service")
    run("systemctl daemon-reload")
    run("systemctl restart docker")
    run("systemctl restart kubelet")


def setting():
    if HA:
        master_ip = FLOAT_IP
    else:
        master_ip = MASTER_HOSTS[0]

    local('cp ' + LOCAL_DIR + '/bin/kubectl /usr/local/bin/kubectl')
    local('chmod +x /usr/local/bin/kubectl')
    local('kubectl config set-cluster kubernetes'
          ' --certificate-authority=' + TMP_DIR + '/ssl/ca/ca.pem'
          ' --embed-certs=true'
          ' --server=https://' + master_ip + ':' + str(ADVICE_MASTER_PORT))
    local('kubectl config set-credentials admin'
          ' --client-certificate=' + TMP_DIR + '/ssl/admin/admin.pem'
          ' --embed-certs=true --client-key=' + TMP_DIR + '/ssl/admin/admin-key.pem')
    local('kubectl config set-context kubernetes --cluster=kubernetes --user=admin')
    local('kubectl config use-context kubernetes')

    local('kubectl apply -f ' + LOCAL_DIR + '/master/script/auto-csr-rbac.yaml')
    local(
        'kubectl create clusterrolebinding kubelet-bootstrap --clusterrole=system:node-bootstrapper --user=kubelet-bootstrap')
    local(
        'kubectl create clusterrolebinding node-client-auto-approve-csr --clusterrole=approve-node-client-csr --group=system:bootstrappers')
    local(
        'kubectl create clusterrolebinding node-server-auto-renew-crt --clusterrole=approve-node-server-renewal-csr --group=system:nodes')
    local(
        'kubectl create clusterrolebinding node-client-auto-renew-crt --clusterrole=approve-node-client-renewal-csr --group=system:nodes')
    local('kubectl create clusterrolebinding system-node-role-bound --clusterrole=system:node --group=system:nodes')


def proxy():
    if HA:
        master_ip = 'https://' + FLOAT_IP + ':' + str(ADVICE_MASTER_PORT)
    else:
        master_ip = 'https://' + MASTER_HOSTS[0] + ':' + str(ADVICE_MASTER_PORT)
    local('kubectl config set-cluster kubernetes'
          ' --certificate-authority=' + TMP_DIR + '/ssl/ca/ca.pem'
          ' --embed-certs=true'
          ' --server=https://' + master_ip + ':' + str(ADVICE_MASTER_PORT) +
          ' --kubeconfig=' + TMP_DIR + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl config set-credentials kube-router'
          ' --client-certificate=/tmp/ssl/kube-router/kube-router.pem'
          ' --client-key=/tmp/ssl/kube-router/kube-router-key.pem'
          ' --embed-certs=true'
          ' --kubeconfig=' + TMP_DIR + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl config set-context default'
          ' --cluster=kubernetes'
          ' --user=kube-router'
          ' --kubeconfig=' + TMP_DIR + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl config use-context default --kubeconfig=' + TMP_DIR + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl create configmap'
          ' -n kube-system kube-router-kubeconfig'
          ' --from-file=' + TMP_DIR + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl apply -f ' + LOCAL_DIR + '/master/plugin/kube-router/kuberoute.yaml')


def network():
    if CNI == 'flannel':
        local('kubectl apply -f ' + LOCAL_DIR + '/master/plugin/flannel')


def core_dns():
    local('cp ' + LOCAL_DIR + '/master/plugin/coredns/coredns.yaml ' + TMP_DIR)
    local('sed -i "s/__CLUSTER_DNS_IP__/' + CLUSTER_DNS_IP + '/g" ' + TMP_DIR + '/coredns.yaml')
    local('kubectl apply -f ' + TMP_DIR + 'coredns.yaml')

