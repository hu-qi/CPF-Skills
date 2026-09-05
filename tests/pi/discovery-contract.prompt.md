请严格依据已加载的 `thirdparty-library-discovery` Skill 完成一次离线契约测试。

约束：

- 不要联网，不要调用外部搜索，不要补充任何未提供的事实；
- 只根据下面提供的模拟证据判断状态；
- 不要因为“没看到适配”就推断“没有适配”；
- 输出一个 Markdown 表格，列为：`candidate | status | reason`；
- `status` 列必须使用 Skill 中定义的英文规范状态 token，不得翻译、缩写或改写；
- 每个候选只能给出一个最终状态；
- `reason` 可以使用中文解释。

候选与证据：

1. `AlphaPlugin`
   - Flutter 插件，当前仍维护；
   - 明确包含平台原生实现，因此技术上可能需要鸿蒙适配；
   - 常规包中心检索暂未发现 OpenHarmony/HarmonyOS 支持；
   - CPF-Flutter 官方 `flutter-library-search` 和 `ohos-flutter-plugin-adaptation-necessity-check` 本次均不可用；
   - 活动要求的 CPF-Flutter / hxa-flutter 等必查去重源尚未全部完成验证。

2. `BetaPlugin`
   - Flutter 插件；
   - CPF-Flutter 官方 `flutter-library-search` 已明确返回：该库已有可用鸿蒙适配实现。

3. `GammaPackage`
   - Flutter 包；
   - 官方适配必要性检查已明确确认：该包为纯 Dart 实现，不依赖平台原生能力，不需要进行鸿蒙平台适配。

请直接给出表格，不要输出额外候选。
