# 自定义私有服务器 API

FitTrack 不附带任何真实服务地址、真实接口路径或凭证。使用者填写自己的私有服务器地址；默认留空时，只有离线演示可以直接运行，sync 会在发出网络请求前提示补全配置。

## 填空配置

四个配置项见 [配置模板](../.env.example)，它们的值均为空：

```dotenv
FITTRACK_TRAINING_API_URL=
FITTRACK_BODY_API_URL=
FITTRACK_TRAINING_TOKEN=
FITTRACK_BODY_TOKEN=
```

将训练读取接口的完整 URL、身体数据读取接口的完整 URL，以及各自的 Bearer 凭证填入当前进程的环境变量。地址由使用者自行提供，没有默认域名或拼接的固定路径。

例如在 PowerShell 中逐项填写引号内的空白：

```powershell
$env:FITTRACK_TRAINING_API_URL = ""
$env:FITTRACK_BODY_API_URL = ""
$env:FITTRACK_TRAINING_TOKEN = ""
$env:FITTRACK_BODY_TOKEN = ""
```

.env.example 是填写说明，不会被程序自动加载。若自行复制为 .env 保存配置，应仅放在本地，并通过自己的环境加载工具导出。.env 和 private/ 已被 Git 忽略，真实配置不得提交到仓库。

填好后运行：

```bash
fittrack --db private/fitness.sqlite3 sync --date 2026-01-15
fittrack --db private/fitness.sqlite3 history --source server --start 2026-01-01 --end 2026-01-31
```

## 私有服务器需要实现的数据契约

两个接口均接收 JSON POST 请求，使用 Authorization: Bearer <用户自己的凭证>，请求体为：

```json
{"date": "2026-01-15"}
```

训练接口返回：

```json
{"complete": true, "sessions": []}
```

身体接口返回：

```json
{"complete": true, "body": []}
```

数组里的字段使用 FitTrack 的规范化格式，完整虚构例子见 [minimal-synthetic.json](../examples/minimal-synthetic.json)。sessions 包含场次、动作和组；body 包含日期、指标、数值、单位和可选测量时刻。

服务器应先完成自己的分页、字段映射和来源校验，再返回当天的完整数据；未完成时返回 complete: false，FitTrack 将拒绝整批导入。正常休息日或无测量时可以返回空数组，但不能把尚未读取的数据标记为完整。返回记录的日期必须与请求日期一致。

这是明确的数据契约，不代表能自动识别任何第三方 API。使用者的私有服务器若接入训记或其他来源，需要自行在服务端映射为该格式，并取得相应授权。仓库不提供真实来源接口地址或私有开发者协议。

## 行为与验证范围

仅在显式执行 sync 时读取配置。请求有超时、响应大小限制和 gzip 支持，拒绝跳转，不打印服务器地址、请求凭证或原始错误响应。不进行后台轮询、自动重试或云端数据修改。

器械身份、正式组标记和测量时间由服务器明确提供；未知数据保持为空，不推定为有效预测样本。两份响应通过校验后，才在一个 SQLite 事务中写入。原始服务器响应不保留。

测试使用虚构数据和网络模拟，没有连接真实私有服务器。使用者需要自行验证自己的接口实现、访问权限和服务端只读行为；FitTrack 的 POST 约定表示查询，不授权服务端执行训练或身体数据修改。
