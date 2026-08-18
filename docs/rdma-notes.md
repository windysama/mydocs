# RDMA 驱动验证笔记

记录 RDMA NIC 驱动在内核中的实现要点，以及 **firmware / 芯片层面**的验证思路。
本文为示例文档，用于演示文档站能力，内容可根据实际工作持续补充。

## 1. 驱动与硬件的交互边界

RDMA 网卡驱动的核心职责是在内核中管理：

- **QP（Queue Pair）**：发送/接收队列对，是 RDMA 通信的基本上下文；
- **CQ（Completion Queue）**：完成事件队列；
- **doorbell / 寄存器映射**：通过 `pci_iomap` 将 BAR 映射到内核虚拟地址，
  驱动以此向硬件“敲门”通知有新 WQE 就绪。

```c
/* 示例：映射 NIC 的 BAR0 寄存器空间 */
struct mynic_priv *priv = netdev_priv(netdev);
priv->regs = pci_iomap(pdev, 0, 0);
if (!priv->regs)
        return -ENOMEM;

/* 写 doorbell 通知硬件消费 WQE */
writel(cpu_to_le32(wqe_idx), priv->regs + MYNIC_DB_SQ);
```

!!! note "验证要点"
    寄存器写操作必须使用正确的端序（`cpu_to_le32`），并在写入后确认
    硬件产生了预期的完成事件（CQE），否则可能是 firmware 未按约定解析 WQE。

## 2. Firmware 验证流程

芯片层面的验证通常分三层：

1. **加载校验**：firmware 镜像签名/版本校验通过后，经 `request_firmware`
   加载并由驱动写入设备；
2. **健康探针**：驱动周期性读取 firmware 心跳寄存器，超时则触发恢复；
3. **功能回归**：用 `ibv_*` 用户态工具跑基本 verbs 通路（send/recv、RDMA write），
   对比 golden 结果。

```bash
# 基本连通性验证（需两端节点）
ibv_devinfo                 # 确认设备被内核识别
ibv_send_lat -d mlx5_0      # 测 send/recv 延迟
ibv_write_bw -d mlx5_0      # 测 RDMA write 带宽
```

## 3. 常见调试手段

| 现象 | 可能原因 | 排查方式 |
|------|----------|----------|
| CQE 长时间不返回 | doorbell 未生效 / WQE 格式错 | 抓寄存器、对比 WQE 布局 |
| firmware 加载失败 | 版本不匹配 / 签名错误 | 看 `dmesg`，核对 `request_firmware` 返回 |
| 带宽不达标 | MTU / QP 数量 / 中断亲和 | `ethtool -i`、perf 采样 |

!!! warning "注意"
    修改 firmware 相关代码前务必确认有 **回滚镜像**，避免设备进入不可恢复状态。

## 4. 小结

驱动的健壮性与 firmware 验证密不可分：寄存器交互、加载校验、健康探针
三者任一环节疏漏，都会表现为上层 verbs 异常。建议把每条通路都配上可重复的
回归脚本，纳入 CI 长期盯防。
