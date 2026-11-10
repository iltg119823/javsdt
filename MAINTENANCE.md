# 维护记录

基于 IzumiHoshi/javsdt master，2026-11-10。

- 修复 JavDB 代理分支 requests 的 header 参数拼写错误。
- 修复 HTTP 代理类型判断和 HTTPS 目标的 HTTP CONNECT 代理地址。
- 补充缺失的 lxml；升级 Requests / Pillow，使用 openpyxl 读取 xlsx。
- 去除 Python 3.12 已删除的 distutils 的无用导入。
- 使用 Pillow Resampling.LANCZOS 替换已移除的 ANTIALIAS。
- 特征表、素人编号表改为相对于源码定位；关闭 Excel 与配置写入文件。
- 未知网站特征保留原值，避免新特征令整理中断。
- 启动直接处理所选目录，不再预先搬运子目录视频到 Build；无效路径退出。
- 新增 7 项回归测试，Python 3.12.14 下全部通过，pip check 通过。

测试覆盖代理请求参数、实际生成的配置、真实 Excel 数据、图片水印、入口导入、
启动目录传递及取消选择。没有使用用户真实影片，也未完成在线抓取到归档的端到端验证。
Windows exe 未构建。配置中的旧数据源地址可能不可用，需要结合用户报错继续诊断。
