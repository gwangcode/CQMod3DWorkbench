import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import MagicMock
import terminal

def test_terminal_execution_namespace():
    """测试终端执行代码时，是否正确注入了变量"""
    # 绕过 Qt 的初始化，直接实例化并 mock 掉 UI 部分
    term = terminal.PythonTerminal()
    
    # 赋予假的 UI 方法防止报错
    term.write = MagicMock()
    term.insertPlainText = MagicMock()
    
    # 1. 测试基本变量赋值
    term.execute_code("test_x = 42")
    assert term.local_vars.get("test_x") == 42
    
    # 2. 测试是否能调用预设的 show 函数
    term.local_vars["show"] = MagicMock()
    term.execute_code("show('dummy_model')")
    term.local_vars["show"].assert_called_once_with("dummy_model")
    
    # 3. 测试多行代码执行
    code = """
def multiply(a, b):
    return a * b
res = multiply(3, 4)
"""
    term.execute_code(code)
    assert term.local_vars.get("res") == 12

def test_terminal_error_handling():
    """测试终端遇到错误时，是否会捕获并输出 Traceback"""
    term = terminal.PythonTerminal()
    term.write = MagicMock()
    
    # 故意执行一段有语法错误的代码
    term.execute_code("print(1/0)")
    
    # 验证是否调用了 write 把报错信息打出来了
    term.write.assert_called_once()
    assert "ZeroDivisionError" in term.write.call_args[0][0]
