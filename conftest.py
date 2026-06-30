"""
pytest 根配置
=============

是什么:项目根的 conftest,保证测试进程能 `import backend.collaboration`。
做什么:把项目根目录加入 sys.path(放在最前),让 `backend` 作为顶层包可导入。
不做什么:不定义 fixture(各测试文件自带 reset_state fixture)。
对外暴露:无(pytest 自动加载)。
"""

import os
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
