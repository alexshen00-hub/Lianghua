
# 量化选股工具（Streamlit Demo）

这是一个零配置的可视化 **量化选股演示应用**。核心做法：
- 使用（可选）Akshare 获取A股日线行情；也支持手动上传CSV数据。
- 计算简化的打分：成交量缩放、均线形态、突破、套牢盘、形态/枢轴、题材/事件（占位）以及负面因子。
- 输出综合分 `Total = S + Δ * 2.7 - P`，并支持Top榜单、单票走势查看、CSV下载。

> **免责声明**：仅作教育演示，不构成投资建议。

## 在线部署（Streamlit Cloud）

1. 将本目录代码推送到你的 GitHub 仓库。
2. 访问 [https://share.streamlit.io](https://share.streamlit.io) 登录并创建新应用：
   - 指定仓库、主分支
   - 指定入口文件：`app.py`
3. 等待构建完成后，即可获得一个公开的网址，直接在浏览器使用。

## 本地运行

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 使用要点
- 若 **Akshare 可用**：勾选侧边栏“使用 Akshare 获取A股”，会自动拉取A股股票列表与日线数据（前复权）。
- 若 **Akshare 不可用** 或网络受限：
  - 取消勾选，使用内置示例代码列表，或
  - 上传你自己的历史行情 **CSV**（需要包含列：`date, open, high, low, close, volume`）。
- 你可以在侧边栏输入自定义股票代码（逗号分隔）。

## 自定义/扩展
- 将“事件/题材”替换为公告/新闻/板块热度数据；
- 引入更多技术/基本面因子（ROE、PE、现金流等）；
- 增加回测模块（如 vectorbt / backtrader）；
- 增加风险控制（最大回撤、仓位管理）。
