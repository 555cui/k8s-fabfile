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
tmp_dir = '/k8s-tmp'


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
    local('mkdir -p' + tmp_dir +'/ssl')
    local('cp -r ' + WORK_DIR + '/ssl/config' + tmp_dir + '/ssl/')

    api_file_path = WORK_DIR + '/ssl/config/apiserver-csr.json'
    etcd_file_path = WORK_DIR + '/ssl/config/etcd-csr.json'

    local(get_replace_format('__CLUSTER_API_IP__', cluster_ip, api_file_path))
    local(get_replace_format('__MASTER_HOSTS__', master_hosts, api_file_path))

    local(get_replace_format('__ETCD_HOSTS__', etcd_hosts, etcd_file_path))


@roles('etcd')
def etcd():
    # 分发软件包和证书
    run('mkdir -p ' + BASE_DIR + '/ssl')
    put(WORK_DIR + '/etcd', BASE_DIR + '/')
    put(tmp_dir + '/ssl/etcd', BASE_DIR + '/ssl/')
    put(tmp_dir + '/ssl/ca', BASE_DIR + '/ssl/')

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
    run('mkdir -p ' + BASE_DIR + '/ssl')
    put(WORK_DIR + '/master', BASE_DIR + '/')
    put(tmp_dir + '/ssl/etcd', BASE_DIR + '/ssl/')
    put(tmp_dir + '/ssl/apiserver', BASE_DIR + '/ssl/')
    put(tmp_dir + '/ssl/metrics', BASE_DIR + '/ssl/')
    put(tmp_dir + '/ssl/ca', BASE_DIR + '/ssl/')

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
        run('rm -rf ' + tmp_dir)
        run('mkdir -p ' + tmp_dir)
        put(WORK_DIR + '/docker/package', tmp_dir + '/')
        # 离线安装docker
        run("rpm -ivh " + tmp_dir + "/package/libtool-ltdl-2.4.2-22.el7_3.x86_64.rpm")
        run("rpm -ivh " + tmp_dir + "/package/containerd.io-1.2.0-3.el7.x86_64.rpm")
        run("rpm -ivh " + tmp_dir + "/package/docker-ce-18.09.0-3.el7.x86_64.rpm")
        run("rpm -ivh " + tmp_dir + "/package/container-selinux-2.66-1.el7.noarch.rpm")
        run("rpm -ivh " + tmp_dir + "/package/docker-ce-18.09.0-3.el7.x86_64.rpm")

    # 覆盖docker配置文件
    run("mkdir -p /etc/docker")
    put(WORK_DIR + '/docker/daemon.json', '/etc/docker/')

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
          ' --certificate-authority=' + tmp_dir + '/ssl/ca/ca.pem'
          ' --embed-certs=true'
          ' --server=https://' + master_ip + ':' + str(ADVICE_MASTER_PORT) +
          ' --kubeconfig=' + tmp_dir + '/kubeconfig/bootstrap.kubeconfig')
    local('kubectl config set-credentials kubelet-bootstrap'
          ' --token=' + BOOTSTRAP_TOKEN +
          ' --kubeconfig=' + tmp_dir + '/kubeconfig/bootstrap.kubeconfig')
    local('kubectl config set-context default'
          ' --cluster=kubernetes'
          ' --user=kubelet-bootstrap'
          ' --kubeconfig=' + tmp_dir + '/kubeconfig/bootstrap.kubeconfig')
    local('kubectl config use-context default --kubeconfig=' + tmp_dir + '/kubeconfig/bootstrap.kubeconfig')

    # 分发软件包和配置
    put(WORK_DIR + '/worker', BASE_DIR + '/')
    run('mkdir /opt/cni')
    put(WORK_DIR + '/cni/bin', '/opt/cni/')
    put(tmp_dir + '/kubeconfig', BASE_DIR + '/worker/')
    # ToDo 获取私网IP
    private_ip = env.host

    run('chmod +x /opt/cni/bin/*')
    run("sed -i 's/__HOSTNAME_OVERRIDE__/" + private_ip + "/g' " + BASE_DIR + "/worker/config/kubelet.conf")
    run('mkdir /etc/cni')
    put(WORK_DIR + '/cni/net.d', '/etc/cni/')

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

    local('cp ' + WORK_DIR + '/bin/kubectl /usr/local/bin/kubectl')
    local('chmod +x /usr/local/bin/kubectl')
    local('kubectl config set-cluster kubernetes'
          ' --certificate-authority=' + tmp_dir + '/ssl/ca/ca.pem'
          ' --embed-certs=true'
          ' --server=https://' + master_ip + ':' + str(ADVICE_MASTER_PORT))
    local('kubectl config set-credentials admin'
          ' --client-certificate=' + tmp_dir + '/ssl/admin/admin.pem'
          ' --embed-certs=true --client-key=' + tmp_dir + '/ssl/admin/admin-key.pem')
    local('kubectl config set-context kubernetes --cluster=kubernetes --user=admin')
    local('kubectl config use-context kubernetes')

    local('kubectl apply -f ' + WORK_DIR + '/master/script/auto-csr-rbac.yaml')
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
          ' --certificate-authority=' + tmp_dir + '/ssl/ca/ca.pem'
          ' --embed-certs=true'
          ' --server=https://' + master_ip + ':' + str(ADVICE_MASTER_PORT) +
          ' --kubeconfig=' + tmp_dir + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl config set-credentials kube-router'
          ' --client-certificate=/tmp/ssl/kube-router/kube-router.pem'
          ' --client-key=/tmp/ssl/kube-router/kube-router-key.pem'
          ' --embed-certs=true'
          ' --kubeconfig=' + tmp_dir + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl config set-context default'
          ' --cluster=kubernetes'
          ' --user=kube-router'
          ' --kubeconfig=' + tmp_dir + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl config use-context default --kubeconfig=' + tmp_dir + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl create configmap'
          ' -n kube-system kube-router-kubeconfig'
          ' --from-file=' + tmp_dir + '/kubeconfig/kube-router.kubeconfig')
    local('kubectl apply -f ' + tmp_dir + '/master/plugin/kube-router/kuberoute.yaml')


def network():
    if CNI == 'flannel':
        local('kubectl apply -f ' + WORK_DIR + '/master/plugin/flannel')


def core_dns():
    local('cp ' + WORK_DIR + '/master/plugin/coredns/coredns.yaml ' + WORK_DIR)
    local('sed -i "s/__CLUSTER_DNS_IP__/' + CLUSTER_IP[1] + '/g" ' + tmp_dir + '/coredns.yaml')
    local('kubectl apply -f ' + tmp_dir + 'coredns.yaml')

