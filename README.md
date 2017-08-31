# packages repo

The packages for rt-thread. 

# [中文版] 包仓库

这个仓库用于存放RT-Thread的软件包信息。RT-Thread包分成两部分，这个仓库中存放的是包的信息：

* Kconfig - 此软件包的配置信息
* package.json - 包的信息，包括不同版本的实际代码包链接指向。

一个软件包可以由env中的包工具：`pkgs --wizard` 来创建软件包的描述。后续通过正确填写链接指向，并把这个包信息提交到目前这份包仓库中，从而分享到RT-Thread社区中供大家使用。
