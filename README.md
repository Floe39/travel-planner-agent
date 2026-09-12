# 多 Agent 旅行规划助手（后端）

基于 LangGraph 的纯后端旅行规划服务。系统将航班、酒店和活动拆成三个专家节点，并行生成候选方案；随后由预算节点进行确定性核算。若方案超支，工作流依次缩减活动、更换低价酒店和航班，再输出可解释的行程方案或预算无解状态。

> 当前数据工具为本地 Mock，项目的重点是 Agent 工作流、状态管理、预算约束和后端工程实践，而非接入真实旅游供应商 API。

## 架构

```text
            ┌─ 航班专家 ─┐
请求 ───────┼─ 酒店专家 ─┼─> 预算核算 ─> [超预算？] ─> 方案生成
            └─ 活动专家 ─┘                  │
                                              └─> 分阶段重规划（活动 → 酒店 → 航班）
```

## 已实现能力

- LangGraph 主图与并行专家节点；使用 fan-in 等待全部专家结果后再执行预算核算。
- 航班、酒店、活动三类 Mock 工具及可替换的数据提供者边界。
- 规则决策引擎：按均衡、舒适、经济偏好选择候选；所有成本均由后端确定性计算。
- 可选 LLM 决策引擎：模型仅从受限候选 ID 中选择；非法 JSON 或服务异常会回退规则引擎，并在响应 `warnings` 中明确标记。
- 超预算时按“缩减活动 → 更换酒店 → 更换航班”的顺序重规划。若最低成本组合仍超预算，返回 `budget_unmet`、最低可行预算与调整建议，而不伪装成成功方案。
- 日期和人数校验、统一错误响应、请求 ID 与结构化访问日志；pytest 覆盖预算内、逐步重规划、预算无解、LLM 降级和 API 合约。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

请求示例：

```bash
curl -X POST http://127.0.0.1:8000/api/trips/plan \
  -H 'Content-Type: application/json' \
  -d '{"destination":"东京","start_date":"2026-10-01","end_date":"2026-10-05","num_travelers":2,"budget":6000,"preference":"comfort"}'
```

默认使用 `PLANNER_MODE=rule`，不需要任何 API Key。若需要由 DeepSeek 等 OpenAI 兼容模型进行候选选择，复制 `.env.example` 为 `.env`，设置 `PLANNER_MODE=llm` 和对应凭据；真实旅游数据仍保持 Mock。

执行测试：

```bash
pytest -q
```

## 后续演进

- 将 `MockTravelDataProvider` 替换为真实航班、酒店或地图 API 适配器。
- 为 LLM 决策增加评测集和成本/时延指标，持续验证结构化选择质量。
- 增加持久化任务记录、异步队列、鉴权、限流、链路追踪与工作流评测。
