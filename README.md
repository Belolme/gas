# 介绍

一个 windows 平台下的原神圣遗物导出小工具. 

# 功能列表

- 导出原神背包中的圣遗物信息
  - 导出格式
    - [莫娜占卜铺](https://www.mona-uranai.com/artifacts)
    - [原魔计算器](https://genshin.mingyulab.com/)
- 根据给定的圣遗物属性条件给圣遗物加锁或解锁, 主要用途在于一键自动标记狗粮, 节省手动筛选上千个圣遗物的时间 (功能开发中, 未实现)

# 使用方法

1. 使用**管理员权限**启动 exe
2. 把原神修改为**窗口运行**, **修改分辨率**为 1280x720 或 1920x1080 或比例为 16x9 的分辨率
   1. 确认界面语言为**简体中文**, 其他文本暂不支持
3. 打开**背包圣遗物**界面
4. 点击 `开始扫描`
5. 等待扫描结束

# 实现逻辑

- 使用 pyside6 开发 UI
- 使用 windows api 操作键鼠并抓取原神窗口截图
- 使用 crnn 文字识别模型识别截图中的圣遗物信息

# 其他相关项目

- [yas - Superfast Genshin Impact artifacts scanner](https://github.com/wormtql/yas/)
- [Amenoma - simple desktop application to scan and export Genshin Impact Artifacts and Materials](https://github.com/daydreaming666/Amenoma)

