# 许可边界(License Boundary)

本文件说明本仓库代码的许可归属。

## 单一许可:专有(Proprietary)

本仓库是独立、通用的协作工具,不包含也不依赖任何第三方项目源码。
全部代码、hook 脚本、文档统一采用**专有许可**:

- 版权所有,保留一切权利。
- 任何使用(个人或企业)均需购买商业许可,详见仓库根目录 `LICENSE`。

## 文件头约定

每个源码文件头部保留两行声明:

```
Collaboration Copyright (c) 2026 P0luz. All rights reserved.
Proprietary. Commercial license required for any use; see LICENSE.
```

## 判断规则

- 新增源码文件 → 加上述文件头。
- 若将来引入任何第三方源码 → 保留其原始许可头,并在 `THIRD_PARTY_NOTICES.md` 登记,不混用许可。
- 不确定某文件归属时,**停下来确认**,不擅自归类。

## 品牌边界检查

提交前可运行:

```powershell
py -3.10 scripts/collaboration-compliance/brand_boundary_check.py
```

该脚本会扫描产品表面与源码中的旧品牌或第三方名称。`plan.md` 和 `requirements.txt`
保留为历史决策/否定性边界说明,默认不参与违规判断。
