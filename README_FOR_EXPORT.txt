米游社工具箱 · 导出说明
导出时间: 2026-08-21 19:25:01 UTC
归档文件: miHoYo_ToolKit-20260821-192339.tar.gz
包含分支: main / docs/project-introduction / refactor/zerotermux-adapter
========================================

【你现在在 Trae APP 文件侧栏能看到这两个文件】：
  1. miHoYo_ToolKit-20260821-192339.tar.gz      ← 真正的项目源码 tar.gz 归档
  2. README_FOR_EXPORT.txt    ← 你现在看的这张说明卡

【如何把 1 号 tar 导出到手机文件管理器（真机 /sdcard 任意目录）】：

  A. 在 Trae APP 「文件」面板里：
        长按 miHoYo_ToolKit-20260821-192339.tar.gz
        → 弹出菜单选 『导出』或『共享』或『保存到手机』
        → 在系统弹出的「存储访问框架 SAF」界面，选：
             内部存储 → LingLan → material → github → Vers123
             （若目录不存在，SAF 界面右下角一般都能「新建文件夹」）
        → 点『保存』

  B. A 找不到时的最简单通用路径（一定能看到）：
        长按 miHoYo_ToolKit-20260821-192339.tar.gz → 『共享/发送』 → 选系统自带的『下载』或『文件』
        或者直接另存到 内部存储 → Download

  C. 如果 Trae APP 里没有『导出』菜单，可以改用：
        选中 tar 包 → 「复制」→ 打开手机文件管理器
        → 进入 LingLan/material/github/Vers123 → 「粘贴」

【真机里解压命令】（ZeroTermux 或任意终端模拟器里）：
    mkdir -p ~/miHoYo_ToolKit
    tar -xzf "内部存储/LingLan/material/github/Vers123/miHoYo_ToolKit-20260821-192339.tar.gz" -C ~/miHoYo_ToolKit
    # 或在文件管理器里直接点 tar 包用 MT管理器/ES文件浏览器 解压

【验证完整性】（解压后 cd 到目录里执行）：
    git branch
    # 期望输出 3 个分支：
    #   docs/project-introduction
    #   main
    # * refactor/zerotermux-adapter
