# k8s-fabfile for
fab version 1.14.0
k8s version 1.13.0
基于python fabfile一键部署k8s

# 准备
+ BASE_DIR 目标机器安装目录
+ WORK_DIR 本地软件包位置

# 本地软件包内容
+ /bin
+ /config
+ /script

预配置
````
fab prepare
````
生成ssl
````
fab ssl
````
部署etcd
````
fab etcd
````
部署master
````
fab master
````
部署docker
````
fab docker
````
部署worker
````
fab worker
````
部署kube-router
````
fab kuberoute
````