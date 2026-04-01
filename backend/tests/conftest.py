"""Pytest配置文件"""

import os
import sys

import pytest

# 确保可以导入backend模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
