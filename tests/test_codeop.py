import codeop

def test_multiline_detection():
    """测试代码是否被正确识别为未完成、完整或语法错误"""
    
    # 1. 未完成的代码（需要缩进）
    incomplete = "for i in range(3):"
    assert codeop.compile_command(incomplete, "<input>", "exec") is None
    
    # 2. 未完成的代码（括号没闭合）
    incomplete_bracket = "print('hello'"
    assert codeop.compile_command(incomplete_bracket, "<input>", "exec") is None
    
    # 3. 完整的单行代码
    complete = "x = 1 + 1"
    assert codeop.compile_command(complete, "<input>", "exec") is not None
    
    # 4. 完整的多行代码
    complete_multi = "def foo():\n    return 1"
    assert codeop.compile_command(complete_multi, "<input>", "exec") is not None
