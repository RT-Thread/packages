# RT-Thread软件包仓库

[![Build Status](https://travis-ci.org/RT-Thread/packages.svg)](https://travis-ci.org/RT-Thread/packages)[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat)](https://github.com/RT-Thread/packages/pulls)

 [[English]](README_en.md)

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

# 注意
1. 提交前请确认Kconfig以及package.json文件的编码格式为UTF-8格式，否则会导致env报错。
2. 软件包的仓库名称不要以数字开头，否则gitee备份中国大陆镜像源时，备份不过去。
3. 软件包内请不要包含submodule，gitee中国大陆镜像源无法备份submodule的内容，会导致用户直接使用github拉取软件包，可能会断流。
4. 需要采用github作为软件包托管仓库，不要使用gitee，后台会自动创建gitee大陆镜像源。
5. 在你的软件包索引被合并之后，请于次日或后日到[RTT软件包中国gitee镜像源组织](https://gitee.com/RT-Thread-Mirror)中查看是否增加了你的软件包仓库（每日凌晨会有机器人自动同步），如果没有增加和同步，请在github提issue与管理员联系。
6. 可以在提交之前使用vscode或者是json语法检查工具检查json的语法是否正确，以免引发自检机器人报错
7. 如果是将第三方设计的开源项目注册到RT-Thread软件包中心，尽量fork该项目（也称之为上游项目），方便日后同步上游修改，[例如](https://github.com/flyingcys/rpmsg-lite)。或者如果上游项目同意添加RT-Thread的Sconscript，可以直接将上游项目直接注册为RT-Thread软件包，[例如](https://github.com/lvgl/lvgl)

## 感谢以下小伙伴对本仓库的贡献！

<a href="https://github.com/RT-Thread/packages/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=RT-Thread/packages" />
</a>
