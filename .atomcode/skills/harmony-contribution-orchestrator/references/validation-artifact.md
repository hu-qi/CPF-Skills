# Validation Artifact Contract

本文件定义 `harmony-contribution-orchestrator` 在适配完成后使用的确定性验证输入。

实现位于：

```text
scripts/orchestrator/resolve_validation_gate.py
```

## 目标

Validation Gate 只回答：

> 当前是否已经有足够的真实技术证据，可以从 `VALIDATION` 进入 `ARTICLE_PREP`？

它不判断文章内容质量，也不替代框架官方测试/检查 Skill。

## 必需检查

`validation.checks` 必须且只能包含以下 6 项：

1. `implementation`：存在真实代码变更/实现产物；
2. `build`：目标工程或库构建成功；
3. `demo`：存在可运行 Demo 或最小使用场景；
4. `tests`：关键功能测试已执行并通过；
5. `device_run`：已在 HarmonyOS/OpenHarmony **实体设备**成功运行；
6. `screenshots`：存在可用于文章的真实成功运行截图。

## 状态 token

每项检查只能使用：

```text
VERIFIED
FAILED
NOT_RUN
MISSING
```

含义：

- `VERIFIED`：已经完成且有证据；
- `FAILED`：已执行但失败，必须修复后重验；
- `NOT_RUN`：尚未执行；
- `MISSING`：应存在的产物/证据缺失。

不得创建同义状态。

## Evidence 规则

每个检查都必须包含 `evidence` 数组。

- `VERIFIED` 时 `evidence` 至少包含一个非空引用；
- `FAILED` 可引用失败日志、测试报告等；
- `NOT_RUN` / `MISSING` 可为空；
- evidence 只保存真实存在的路径、URL、commit、日志、报告、截图等引用；
- 不能把文字描述本身当成“已验证证据”。

典型引用示例：

```text
commit://abc123
file://example/entry/src/main/ets/pages/Index.ets
log://artifacts/build.log
report://artifacts/tests.xml
image://artifacts/device-run.png
```

实际流水线可以采用其他引用格式，只要引用非空且能够定位真实产物。

## 真机约束

`device_run` 在 `VERIFIED` 时还必须提供：

```json
{
  "details": {
    "device_kind": "physical",
    "platform": "HarmonyOS",
    "device_model": "optional model name"
  }
}
```

`platform` 只接受：

```text
HarmonyOS
OpenHarmony
```

模拟器、预览器、Android/iOS 设备不能满足本活动的真机运行门禁。

## 完整输入示例

```json
{
  "framework": "arkts",
  "candidate": "example-library",
  "validation": {
    "checks": {
      "implementation": {
        "status": "VERIFIED",
        "evidence": ["commit://abc123"]
      },
      "build": {
        "status": "VERIFIED",
        "evidence": ["log://artifacts/build.log"]
      },
      "demo": {
        "status": "VERIFIED",
        "evidence": ["file://example/"]
      },
      "tests": {
        "status": "VERIFIED",
        "evidence": ["report://artifacts/tests.xml"]
      },
      "device_run": {
        "status": "VERIFIED",
        "evidence": ["log://artifacts/device-run.log"],
        "details": {
          "device_kind": "physical",
          "platform": "HarmonyOS",
          "device_model": "Example Device"
        }
      },
      "screenshots": {
        "status": "VERIFIED",
        "evidence": ["image://artifacts/device-run.png"]
      }
    }
  }
}
```

## 输出语义

### 全部通过

六项全部为 `VERIFIED` 且满足证据约束：

```text
phase = ARTICLE_PREP
decision = PROCEED
```

### 存在失败或缺项

任一项为 `FAILED` / `NOT_RUN` / `MISSING`：

```text
phase = VALIDATION
decision = BLOCKED
```

并把失败/缺项转换成 `pending_checks`。

### 契约错误

以下情况不是普通 `BLOCKED`，而是输入 artifact 无效，应直接拒绝：

- 缺少任一 required check；
- 出现未知 check；
- 状态 token 非法；
- `VERIFIED` 没有 evidence；
- `device_run=VERIFIED` 但不是 physical device；
- `device_run=VERIFIED` 但平台不是 HarmonyOS/OpenHarmony。

## 边界

Validation Gate 证明的是“文章准备所需技术证据已齐”，不是：

- 文章已经写完；
- 文章已经通过活动合规检查；
- CSDN 质量分已经达到要求；
- 发布后阅读量已经达到目标。

这些属于后续 `ARTICLE_PREP` / `ARTICLE_CHECK` / 发布后跟踪阶段。
