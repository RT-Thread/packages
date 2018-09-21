# packages repo

[![Build Status](https://travis-ci.org/RT-Thread/packages.svg)](https://travis-ci.org/RT-Thread/packages)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)](https://github.com/RT-Thread/packages/pulls)

The packages repo for rt-thread. In this git repo, there is only the information of packages. Some packages maintained by RT-Thread team, is hosted in https://github.com/RT-Thread-packages.

# [中文版] 包仓库

这个仓库用于存放RT-Thread的软件包信息。RT-Thread包分成两部分，包信息和软件包。这个仓库中存放的是包信息（有的时候也可以称为包索引，会直接出现在menuconfig配置工具中）：

* Kconfig - 此软件包的配置信息
* package.json - 包的信息，包括不同版本的实际代码包链接指向。

一个软件包可以由env中的包工具：`pkgs --wizard` 来创建软件包的描述。后续通过正确填写链接指向，并把这个包信息提交到目前这份包仓库中，从而分享到RT-Thread社区中供大家使用。

# 使用方法
1. 下载env环境后，进入env根目录下的packages文件夹。
2. 使用`git clone https://github.com/RT-Thread/packages.git`命令将最新的packages repo 克隆到本地。注：使用方法还可以参考env根目录下的readme.md文件中包管理器使用的章节，可以利用env环境中支持的包管理命令来更新本地packages文件夹。
3. 保证bsp目录中存在Kconfig文件，如果不存在可以参考env工具中的KConfig文件。
4. 双击打开env根目录下的console控制台，通过cd命令进入到需要配置的bsp根目录。然后使用`menuconfig`命令打开env的配置界面，这时即可在RT-thread online packages菜单中找到可以在线下载的组件包。
5. 勾选所需要的组件包后保存并退出，使用`pkgs --update`命令更新项目后，即可在bsp目录下的packages文件夹中找到已经下载&安装好的组件包。
