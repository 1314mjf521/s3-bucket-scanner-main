"""文件名清理工具模块"""
import re


def filter_filename(filename: str, replacement: str = '_') -> str:
    """
    过滤Windows和Excel文件名非法字符
    
    Args:
        filename: 原始文件名
        replacement: 替换字符，默认使用下划线 _
    
    Returns:
        清理后的合法文件名
    
    非法字符列表（Windows和Excel）：
    - : （冒号）
    - \\ （反斜杠）
    - / （正斜杠）
    - ? （问号）
    - * （星号）
    - [ （左方括号）
    - ] （右方括号）
    - # （井号）
    - & （ampersand）
    - 控制字符（ASCII 0-31，除了 tab、LF、CR）
    """
    if not filename:
        return filename
    
    # Windows和Excel非法字符的正则表达式
    # 包括控制字符（ASCII 0-31，除了 tab、LF、CR）
    # 以及 Windows 文件名非法字符
    illegal_chars = r'[\x00-\x08\x0B\x0C\x0E-\x1F:\\/?*[\]#&]'
    
    # 替换非法字符
    cleaned = re.sub(illegal_chars, replacement, filename)
    
    # 限制文件名长度不超过255字符
    if len(cleaned) > 255:
        # 保留扩展名，截取文件名主体
        name_part, ext_part = _split_filename(cleaned)
        max_name_len = 255 - len(ext_part)
        cleaned = name_part[:max_name_len] + ext_part
    
    # 如果文件名为空，返回默认名称
    if not cleaned or cleaned.strip() == '':
        return 'unnamed_file'
    
    return cleaned


def filter_sheet_name(sheet_name: str, replacement: str = '_') -> str:
    """
    过滤Excel工作表名称非法字符
    
    Args:
        sheet_name: 原始工作表名称
        replacement: 替换字符，默认使用下划线 _
    
    Returns:
        清理后的合法工作表名称
    
    Excel工作表名称限制：
    - 不能包含: \ / ? * [ ]
    - 长度不能超过31个字符
    - 不能以单引号开头或结尾
    """
    if not sheet_name:
        return 'Sheet'
    
    # Excel工作表非法字符（不包括#和&，因为它们在工作表名称中是允许的）
    illegal_chars = r'[:\\/?\*\[\]]'
    
    # 替换非法字符
    cleaned = re.sub(illegal_chars, replacement, sheet_name)
    
    # 去除首尾空格
    cleaned = cleaned.strip()
    
    # 如果为空，返回默认名称
    if not cleaned:
        return 'Sheet'
    
    # 限制长度为31个字符
    if len(cleaned) > 31:
        cleaned = cleaned[:31]
    
    return cleaned


def _split_filename(filename: str) -> tuple:
    """
    分离文件名和扩展名
    
    Args:
        filename: 完整文件名
    
    Returns:
        (文件名主体, 扩展名) 元组
    """
    # 查找最后一个点的位置
    last_dot = filename.rfind('.')
    
    if last_dot == -1 or last_dot == 0:
        # 没有扩展名或以点开头（隐藏文件）
        return (filename, '')
    
    return (filename[:last_dot], filename[last_dot:])
