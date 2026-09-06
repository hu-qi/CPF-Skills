# E2E Fixture（仅用于回归测试）

此目录用于验证 `qualification → Validation Gate → Article Material Pack → Static Check → Compliance Report` 的文件接口和状态机是否能够端到端串联。

**这里不是一个真实适配案例。**

所有 JSON 输入都包含：

```json
{
  "fixture_only": true
}
```

所有“证据”引用都使用：

```text
fixture://...
```

因此：

- 不得把本目录当作真实征文素材；
- 不得把 `ExampleLibrary` 当作真实活动候选；
- 不得把 `FixtureDevice` 当作真实设备运行记录；
- 不得把 fixture 的 `READY_TO_PUBLISH` 当作真实文章发布资格；
- 真实案例必须使用可追溯到真实仓库、构建日志、测试报告、实体 HarmonyOS/OpenHarmony 设备和截图的证据。

## `READY_TO_PUBLISH` 与 `publishable`

本 fixture 会故意覆盖完整 compliance 的成功状态分支，因此测试结果允许：

```text
status = READY_TO_PUBLISH
```

但确定性 report 必须同时保持：

```text
fixture_only = true
publishable = false
```

这里的 `READY_TO_PUBLISH` 只表示“这组测试数据覆盖到了成功状态机分支”，**不表示现实文章可发布**。

只有真实输入满足全部规则时才允许：

```text
fixture_only = false
status = READY_TO_PUBLISH
publishable = true
```

## 覆盖链路

```text
qualification.json
      +
validation.json
      ↓
resolve_validation_gate.py
      ↓
ARTICLE_PREP / PROCEED
      +
development-notes.json
      ↓
build_article_material_pack.py
      ↓
material pack

article.md
      ↓
check_article_static.py
      ↓
static report

static report
+ validation gate
+ compliance-context.json
+ resources/article-rules.yaml
      ↓
build_compliance_report.py
      ↓
READY_TO_PUBLISH
fixture_only = true
publishable = false
```

## 回归测试

```bash
python3 tests/unit/test_e2e_article_fixture.py
```

测试同时断言：

1. 输入仍明确标记为 `fixture_only`；
2. Validation Gate 能得到 `ARTICLE_PREP/PROCEED`；
3. Article Material Pack 不产生缺口且禁止整篇 AI 生成；
4. 文章静态检查通过；
5. 完整合规报告能覆盖 `READY_TO_PUBLISH` 分支；
6. fixture compliance 始终 `publishable=false`；
7. `readership` 仍是 `POST_PUBLISH`，不阻塞发布前状态。

真实模式中的 Validation、Article Material Pack 和 Compliance 都会拒绝 `fixture://` 引用，因此不能通过简单删除 fixture 标记来把本目录伪装成真实案例。

这个 fixture 的目标只是验证“程序按契约工作”。当有真实适配项目可提供可审计证据时，应使用 `scripts/evidence/init_real_case.py` 建立独立真实案例工作区，而不是修改本 fixture 去伪装真实证据。
