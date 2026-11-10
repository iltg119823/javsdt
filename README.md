# jav-standard-tool 简称javsdt
简介：收集影视元数据，并规范本地文件（夹）的格式，收集演员头像，为emby、kodi、jellyfin、极影派等影片管理软件铺路。  

## 0、【长远计划】：
1、目前只重写了youma，后续再加上对wuma、suren、fc2的支持；  
2、使用过程不再依赖第三方网站；  
3、界面，类似tinymoviemaneger，方便用户对整理出错的影片手动纠错；  
4、用户可以纠错并回报错误，共同维护；  
5、剧照；  
6、预告片；  

  
## 1、【一般用户】下载及群链接：  
目前2021年2月7日更新的1.1.5版本  推荐使用win10 64位  
[从蓝奏云下载](https://junerain.lanzous.com/ivp8Plg6wza) 或者 [从github下载](https://github.com/javsdt/javsdt/releases/tag/V1.1.5)
  
[前往下载演员头像](https://github.com/javsdt/javsdt/releases/tag/女优头像)   
  
[企鹅群](https://jq.qq.com/?_wv=1027&k=5CbWOpV)  
<!--[电报群](https://t.me/joinchat/PaHhgBaleu_qEgFy_NJlIA)（尽量进企鹅群，电报群真的没时间去了）-->   
  
## 2、[使用说明(还没写完)](https://github.com/javsdt/javsdt/wiki)  
[旧版的使用说明从蓝奏云下载](https://junerain.lanzoui.com/ib0qozg)  

## 3、维护版运行环境

建议使用 Python 3.12（已验证）；依赖声明以 requirements.txt 为准。

```sh
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate
python -m pip install -r requirements.txt
cd src
python CreateIni.py
python Youma.py "D:\待整理影片"
```

首次使用才运行 `CreateIni.py`，它会覆盖当前目录的配置。已有配置请先备份，
并在 `src` 目录运行程序以使用现有配置与图片资源。不传路径时使用目录选择器，
Linux 的图形选择器需要系统安装 tkinter。

先在少量影片的副本上试运行；整理会按配置重命名、移动文件。
维护版直接扫描所选目录及子目录，取消原先启动时自动搬运到 Build 的步骤。
旧配置可继续使用；HTTP 代理类型填写 `http`，SOCKS 代理填写 `socks5`。

默认数据源地址来自 2022 年，不能保证仍可使用。2026-11-10 当前云环境探测中，
`javdb31.com` 和 `www.n53i.com` 返回 HTTP 503；这不能单独证明域名永久失效。
请在配置“其他设置”中填写你能正常访问的对应站点地址。本次维护未确认在线网页
解析、验证码或反爬机制兼容性，也未打包 Windows exe。

验证命令（仓库根目录）：

```sh
python -m unittest discover -s tests -v
python -m pip check
```

## 4、工作流程：  
    （1）用户选择文件夹，遍历路径下的所有文件。  
    （2）文件是jav，取车牌号，到javXXX网站搜索影片找到对应网页。  
    （3）获取网页源码找出“标题”“导演”“发行日期”等信息和DVD封面url。  
    （4）重命名影片文件。  
    （5）重命名文件夹或建立独立文件夹。  
    （6）保存信息写入nfo。   
    （7）下载封面url作fanart.jpg，裁剪右半边作poster.jpg。   
    （8）移动文件夹，完成归类。  
  
## 5、目标效果：  
效果图不放了
!=[image](https://github.com/javsdt/images/blob/master/jav/javsdt/readme/%E7%9B%AE%E6%A0%87%E6%95%88%E6%9E%9C1.png?raw=false)  
!=[image](https://github.com/javsdt/images/blob/master/jav/javsdt/readme/%E7%9B%AE%E6%A0%87%E6%95%88%E6%9E%9C2.png?raw=false)  
!=[image](https://github.com/javsdt/images/blob/master/jav/javsdt/readme/%E7%9B%AE%E6%A0%87%E6%95%88%E6%9E%9C3.jpg?raw=false)  
  
## 6、ini中的用户设置：  
![image](https://github.com/JustMachiavelli/wwwroot/blob/master/README%E7%94%A8%E5%9B%BE/Swellow/ini%E8%AE%BE%E7%BD%AE.PNG)  
  
## 7、其他说明：  
（1）不需要赞助；  
（2）允许对软件进行任何形式的转载；  
（3）代码及软件使用“MIT许可证”，他人可以修改代码、发布分支，允许闭源、商业化，但造成后果与本作者无关。  
