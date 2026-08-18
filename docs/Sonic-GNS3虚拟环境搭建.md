# Sonic-GNS3 虚拟环境搭建

> 本文档覆盖 Ubuntu 和 CentOS 7 两种环境。Ubuntu 环境按官方文档走即可，CentOS 7 环境有较多专属踩坑点，请仔细阅读对应章节。

---

## 一、Ubuntu 环境（推荐，官方支持最好）

### Step 1：安装 GNS3

按照官方文档指导安装：
文档地址：[https://docs.gns3.com/docs/getting-started/installation/linux/](https://docs.gns3.com/docs/getting-started/installation/linux/)

**注意：** 安装前需要配置环境上有 http 或 https 的代理可以翻墙访问外网

---

## 二、CentOS 7 环境（补充章节，已踩坑验证）

> ⚠️ CentOS 7 自带 Python 3.6、QEMU 1.5.3、内核 3.10，版本较老，安装 GNS3 需要处理多处兼容性问题。
> 以下步骤在 CentOS 7.9 + KVM 环境实测通过。

### Step 1：安装基础依赖

```bash
# 1. 装 EPEL 源（提供额外的包）
yum install -y epel-release

# 2. 装依赖包
yum install -y python3 python3-devel python3-pip \
  qemu-kvm libvirt virt-install bridge-utils \
  wireshark-gnome xterm gcc make libpcap-devel git

# 3. 启动 libvirtd
systemctl start libvirtd
systemctl enable libvirtd

# 4. 把用户加到 kvm 和 libvirt 组（不用 sudo 就能用）
usermod -aG kvm,libvirt $USER
# 重新登录后生效
```

### Step 2：安装 GNS3（Python 3.6 兼容版）

> ⚠️ **踩坑点 1：新版 aiohttp 不兼容 Python 3.6**
> CentOS 7 的 Python 是 3.6 版本，直接 `pip install gns3-server` 会装最新版 aiohttp（要求 Python 3.7+），导致安装失败。
> 解决方法：先锁定 aiohttp 版本，再装 GNS3。

```bash
# 先装兼容 Python 3.6 的 aiohttp 版本
pip3 install aiohttp==3.7.4

# 再装 GNS3（指定 2.2.45 版本，亲测可用）
pip3 install gns3-gui==2.2.45 gns3-server==2.2.45

# 如果 pip 装慢，换国内源：
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple aiohttp==3.7.4
pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple gns3-gui==2.2.45 gns3-server==2.2.45
```

验证安装：
```bash
gns3 --version
gns3server --version
# 都输出 2.2.45 即为成功
```

### Step 3：安装 QEMU 并修复路径

> ⚠️ **踩坑点 2：CentOS 7 的 qemu-kvm 路径不在 /usr/bin**
> Ubuntu 的 qemu-system-x86_64 在 `/usr/bin/` 下，但 CentOS 7 的 qemu-kvm 在 `/usr/libexec/qemu-kvm`。
> GNS3 默认找 `/usr/bin/qemu-system-x86_64`，找不到会报 "QEMU binary not found"。

```bash
# 建软链接（最简单的解决方法）
ln -s /usr/libexec/qemu-kvm /usr/bin/qemu-system-x86_64

# 验证
qemu-system-x86_64 --version
# 输出 QEMU emulator version 1.5.3 即为成功
```

### Step 4：安装 uBridge

> ⚠️ **踩坑点 3：最新版 uBridge 不兼容 CentOS 7 内核**
> 最新版 uBridge 需要 `IFLA_BRPORT_ISOLATED` 宏（较新内核才支持），CentOS 7 的 3.10 内核没有，编译报错。
> 解决方法：用兼容 CentOS 7 的旧版本 v0.9.14。

```bash
# 下载 uBridge 0.9.14 源码
cd /root
wget https://github.com/GNS3/ubridge/archive/refs/tags/v0.9.14.tar.gz -O ubridge-0.9.14.tar.gz
tar xzf ubridge-0.9.14.tar.gz
cd ubridge-0.9.14

# 编译安装
make
make install

# 验证
ubridge -v
# 输出 uBridge 0.9.14 即为成功

# 设置 setuid 权限（让 ubridge 能操作网络设备）
chmod u+s /usr/local/bin/ubridge
```

### Step 5：启动 GNS3

```bash
# 图形界面模式（桌面版直接启动）
gns3

# 或者只启动 Server（远程模式用）
gns3server
```

---

## 三、SONiC 镜像准备（通用步骤）

### Step 1：Clone sonic-buildimage

```bash
git clone https://github.com/sonic-net/sonic-buildimage.git
```

### Step 2：下载 SONiC VS 镜像

到 Sonic 官方镜像源下载最新的 VS 镜像：
镜像地址：[https://sonic-build.azurewebsites.net/ui/sonic/pipelines](https://sonic-build.azurewebsites.net/ui/sonic/pipelines)

推荐使用 202505 分支的版本，找到 `sonic-vs.img.gz` 文件下载。

![image-20260817205429592](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817205429592.png)

![image-20260817205529344](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817205529344.png)

![image-20260817205551247](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817205551247.png)

![image-20260817205636150](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817205636150.png)

### Step 3：解压镜像

将 `sonic-vs.img.gz` 解压缩，放到 `sonic-buildimage/platform/vs/` 目录下，确保镜像名称为 `sonic-vs.img`：

```bash
# 解压（注意是纯 gzip 不是 tar.gz，用 gunzip 直接解压）
gunzip sonic-vs.img.gz

# 移动到指定目录
mv sonic-vs.img sonic-buildimage/platform/vs/
```

![image.png](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/1772715214448-0cf5686e-af32-46aa-bd43-03cb824758f0.png)

### Step 4：生成 GNS3 appliance 模板

执行 vs 目录下的 `sonic-gns3a.sh` 脚本，自动生成 GNS3 配置文件（.gns3a）：

```bash
cd sonic-buildimage/platform/vs/
bash sonic-gns3a.sh
```

生成的文件名为 `sonic.gns3a`。

![image.png](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/1772715237012-5dd12678-31d1-4932-8545-311abb895375.png)

---

## 四、GNS3 导入 SONiC 镜像（通用步骤）

### Step 1：打开 GNS3 进行初始化配置

桌面版直接打开 GNS3 应用，初始化配置默认下一步即可。

> ⚠️ **注意：必须先创建项目才能拖设备**
> GNS3 需要先新建项目（File → New project），有了画布之后才能从设备列表拖设备。
> 如果新建项目前就拖设备，会没有任何反应。

### Step 2：导入 SONiC appliance

1. 点击 **File → Import appliance**
2. 选择刚刚生成的 `sonic.gns3a` 配置文件
3. 后续点下一步安装（QEMU binary 路径选择 `/usr/bin/qemu-system-x86_64`）
4. 全部进度条完成后，设备列表中会出现 SONiC 虚拟设备

![image.png](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/1772715347322-c8f8f769-3c36-4d46-a0d5-926e24db4b7d.png)

![image.png](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/1772715398696-b9066118-3b9d-4809-b393-c0f7d0e306bb.png)

![image.png](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/1772715443891-1f0c99bf-7049-46e7-a47c-44c2fb0b0188.png)

![image.png](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/1772715452875-9398dd7b-a602-4b39-9c49-af051dad4e7b.png)

![image.png](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/1772715463990-a9efd566-5738-41bc-9da6-36976e635c92.png)

![image.png](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/1772715507895-d6617fa7-9db7-4408-bea8-4b188b62578d.png)

### Step 3：首次启动后必须重启设备

> 🔴 **很重要！必须重启设备！**
> 否则初次安装完成后，部分容器权限未及时更新导致启动失败。

操作方法：
1. 将 SONiC 设备拖入画布

![image-20260817210443724](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817210443724.png)

1. 右键 → **Start** 启动
2. 等待系统完全启动（约 2-3 分钟）
3. 右键 → **Stop** 停止
4. 右键 → **Start** 再次启动

第二次启动后，所有容器才能正常运行。

![image-20260817205935401](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817205935401.png)

### Step 4：进入 SONiC 系统

将设备拖入画布中，右键 Start，然后右键 **Console** 可进入虚拟设备的 SONiC 系统。

**默认登录账号密码：**

- 用户名：`admin`
- 密码：`YourPaSsWoRd`

登录后可以用 `sudo passwd admin` 修改密码。

![image-20260817210010509](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817210010509.png)

---

## 五、验证环境（必做）

进入 SONiC 控制台后，执行以下命令确认环境完整：

```bash
# 1. 看版本
show version

# 2. 看平台/SKU
show platform summary

# 3. 看容器数量（正常应该有 13 个左右）
docker ps -a

# 4. 看端口
show interfaces status | head -10
```

如果 `docker ps -a` 里有多个 FAILED 状态的容器，按 Step 3 重启一次设备。

![image-20260817210151188](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817210151188.png)

![image-20260817210133344](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817210133344.png)

![image-20260817210120123](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817210120123.png)

![image-20260817210110077](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817210110077.png)

---

## 六、远程访问方案

### 方案 A：Windows GNS3 Web + 远程 GNS3 Server（推荐）

图形界面跑在 Windows 上，设备和计算跑在服务器上，体验最好。

**服务器端配置：**
```bash
# 修改 GNS3 Server 监听所有地址
sed -i 's/^host = .*/host = 0.0.0.0/' ~/.config/GNS3/2.2/gns3_server.conf

# 关闭认证（局域网内使用推荐，省得记密码）
sed -i 's/^auth = True/auth = False/' ~/.config/GNS3/2.2/gns3_server.conf

# 防火墙放行端口
firewall-cmd --add-port=3080/tcp --permanent
firewall-cmd --add-port=5000-10000/tcp --permanent
firewall-cmd --reload

# 启动 GNS3 Server
pkill -f gns3server
nohup gns3server &
```

**Windows 端配置：**
	网页输入服务器ip + 3080端口即可

```web-idl
http://172.17.105.195:3080/
```

![image-20260818112451760](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260818112451760.png)
![[附件/Pasted image 20260818112527.png]]



> ⚠️ 如果跨网段/跨防火墙连不上 3080 端口，联系网络管理员放行，或者用 SSH 隧道转发。

### 方案 B：VNC 远程桌面(未验证)

```bash
# 安装 TigerVNC
yum install -y tigervnc-server

# 设置 VNC 密码（8位以内）
vncpasswd
# 问是否设置 view-only 密码，选 n

# 启动 VNC 服务
vncserver :1 -geometry 1920x1080

# 防火墙放行
firewall-cmd --add-port=5901/tcp --permanent
firewall-cmd --reload
```

Windows 装 VNC Viewer，连接 `服务器IP:5901`。

### 方案 C：xrdp（mstsc 远程桌面）

> ⚠️ **踩坑点 4：CentOS 7 的 xrdp 默认可能只监听 IPv6**
> 配置 `port=3389` 后 `netstat` 只显示 tcp6，但 Linux 双栈模式下 IPv4 理论也能连。
> 如果连不上，检查 SELinux 和防火墙。
>
> 如果连不上，检查设置中的屏幕共享

```bash
# 安装
yum install -y epel-release xrdp tigervnc-server

# 启动
systemctl start xrdp
systemctl enable xrdp

# 防火墙放行
firewall-cmd --add-port=3389/tcp --permanent
firewall-cmd --reload

# 关闭 SELinux（CentOS 7 常见坑）
setenforce 0
# 永久关闭需要改 /etc/selinux/config
```

Windows 用 mstsc 连接服务器 IP。

![image-20260817174642590](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817174642590.png)

---

## 七、性能优化（必做，否则 SONiC 会卡得没法用）

> ⚠️ GNS3 默认配置给的资源太少，SONiC 跑起来会非常慢，一定要调。

### 1. 增加内存和 vCPU

默认配置只有 **2G 内存 + 1 个 vCPU**，SONiC 有 13 个容器，根本不够用。

**修改方法：**

```
方法 A：改模板（新建设备都生效）
Edit → Preferences → QEMU VMs → 选 SONiC → Edit
  General settings:
    RAM: 4096 MB（建议 4G 以上，服务器内存够就给 8G）
    vCPUs: 4（建议 4 核以上）

方法 B：改单个设备（只影响这一台）
右键 SONiC 设备 → Configure → General settings
  RAM: 4096 MB
  vCPUs: 4
```

![image-20260817210231602](Sonic-GNS3%E8%99%9A%E6%8B%9F%E7%8E%AF%E5%A2%83%E6%90%AD%E5%BB%BA.assets/image-20260817210231602.png)

**推荐配置：**

| 服务器内存 | 给 SONiC 的内存 | vCPU | 说明 |
|-----------|---------------|------|------|
| 8G | 2048 MB | 2 | 凑合用，会卡 |
| 16G | 4096 MB | 4 | 流畅 |
| 32G+ | 8192 MB | 4-8 | 非常流畅 |

### 2. 开启 KVM 硬件加速（最重要）

> ⚠️ 纯 QEMU 软件模拟比 KVM 硬件加速慢 5-10 倍，一定要开。

**前提条件：**
- 服务器支持虚拟化（Intel VT-x 或 AMD-V / SVM）
- `/dev/kvm` 设备存在
- 当前用户在 kvm 组里

**开启方法：**

```
Edit → Preferences → QEMU VMs → 选 SONiC → Edit
  Advanced settings:
    勾选 "Enable KVM acceleration"
    或者在 Additional options 里加：-enable-kvm
```

**验证有没有生效：**
```bash
# 启动 SONiC 后执行
ps aux | grep qemu-system-x86_64 | grep -c "enable-kvm"
# 输出大于 0 说明生效了
```

### 3. Console 类型改成 Telnet

默认 Console 可能是 VNC（传画面，慢），改成 Telnet（纯文本，快）：

```
右键设备 → Configure → Console
  Console type: Telnet
```

### 4. 网络加速（virtio）

确保网卡用的是 virtio（半虚拟化网卡，比 e1000 快很多）：

```
Edit → Preferences → QEMU VMs → 选 SONiC → Edit
  Network:
    Adapter type: virtio-net-pci（或 paravirtualized）
```

---

## 八、CentOS 7 环境问题排查速查表

| 问题现象 | 原因 | 解决方法 |
|---------|------|---------|
| pip 装 gns3-server 报错 aiohttp 编译失败 | Python 3.6 太老，新版 aiohttp 不支持 | 先装 `aiohttp==3.7.4`，再装 gns3 |
| 导入 appliance 时报 QEMU binary not found | CentOS 7 的 qemu-kvm 在 /usr/libexec/ | `ln -s /usr/libexec/qemu-kvm /usr/bin/qemu-system-x86_64` |
| 启动设备时报 ubridge is not available | 没装 ubridge，或版本太新编译不过 | 装 ubridge v0.9.14 旧版本 |
| ubridge 编译报错 IFLA_BRPORT_ISOLATED | CentOS 7 内核太旧，不支持这个宏 | 用 ubridge 0.9.14 版本 |
| 拖设备到画布没反应 | 还没建项目 | File → New project 先建项目 |
| docker ps -a 很多容器 FAILED | 首次启动权限问题 | Stop → Start 重启一次设备 |
| Windows 连不上 GNS3 Server (3080) | 防火墙拦了或只监听 localhost | 改 host=0.0.0.0 + 放行防火墙端口 |
| xrdp 连不上，只有 tcp6 监听 | SELinux 或防火墙，或网络层拦截 | 关 SELinux、放行 3389，检查网络防火墙 |

---

## 八、环境信息记录（示例）

| 项目 | 信息 |
|------|------|
| 服务器 IP | 172.17.105.192 |
| 操作系统 | CentOS 7.9 |
| CPU | Hygon（海光），支持 SVM 虚拟化 |
| KVM 加速 | ✅ 可用（/dev/kvm 存在） |
| GNS3 版本 | 2.2.45 |
| QEMU 版本 | 1.5.3（qemu-kvm） |
| uBridge 版本 | 0.9.14 |
| SONiC 版本 | 202505 分支 |
| SONiC 平台 | VS（Force10-S6000 SKU，32 口 40G） |
| 镜像文件 | sonic-buildimage/platform/vs/sonic-vs.img |
