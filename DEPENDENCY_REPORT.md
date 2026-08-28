# QA-Tool 依赖项分析报告

## 系统环境
- **Python版本**: 3.14.0 (64-bit)
- **操作系统**: Windows 10/11 (win32)
- **架构**: AMD64
- **pip版本**: 25.2

## 缺失依赖项列表

### 核心UI框架 (1个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| PySide6 | >=6.5.0 | ❌ 缺失 |

### 数值计算 (4个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| numpy | >=1.26.0 | ❌ 缺失 |
| scipy | >=1.11.0 | ❌ 缺失 |
| pandas | >=2.0.0 | ❌ 缺失 |
| statsmodels | >=0.14.0 | ❌ 缺失 |

### 数据可视化 (2个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| matplotlib | >=3.8.0 | ❌ 缺失 |
| seaborn | >=0.12.0 | ❌ 缺失 |

### 机器学习 (2个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| scikit-learn | >=1.3.0 | ❌ 缺失 |
| shap | >=0.44.0 | ❌ 缺失 |

### 文件处理 (6个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| openpyxl | >=3.1.0 | ❌ 缺失 |
| python-calamine | >=0.3.0 | ❌ 缺失 |
| python-docx | >=1.0.0 | ❌ 缺失 |
| xlsxwriter | >=3.1.0 | ❌ 缺失 |
| docxtpl | >=0.16.0 | ❌ 缺失 |
| Pillow | >=10.0.0 | ❌ 缺失 |

### 报告生成 (2个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| reportlab | >=4.0.0 | ❌ 缺失 |
| Jinja2 | >=3.1.0 | ❌ 缺失 |

### 数据库 (3个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| SQLAlchemy | >=2.0 | ❌ 缺失 |
| pymysql | >=1.0.0 | ❌ 缺失 |
| psycopg2-binary | >=2.9.0 | ❌ 缺失 |

### 硬件通信 (1个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| pyserial | >=3.5 | ❌ 缺失 |

### 安全 (1个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| cryptography | >=42.0 | ❌ 缺失 |

### 打包工具 (1个)
| 包名 | 版本要求 | 状态 |
|------|----------|------|
| nuitka | >=4.0 | ❌ 缺失 |

## 总计: 23个依赖项全部缺失

## 安装计划

### 第1步: 升级pip
```bash
python -m pip install --upgrade pip
```

### 第2步: 安装核心依赖 (按优先级)
```bash
# 数值计算基础
pip install numpy>=1.26.0
pip install scipy>=1.11.0
pip install pandas>=2.0.0

# UI框架
pip install PySide6>=6.5.0

# 数据可视化
pip install matplotlib>=3.8.0
pip install seaborn>=0.12.0
```

### 第3步: 安装文件处理依赖
```bash
pip install openpyxl>=3.1.0
pip install python-calamine>=0.3.0
pip install python-docx>=1.0.0
pip install xlsxwriter>=3.1.0
pip install docxtpl>=0.16.0
pip install Pillow>=10.0.0
```

### 第4步: 安装报告和模板依赖
```bash
pip install reportlab>=4.0.0
pip install Jinja2>=3.1.0
```

### 第5步: 安装机器学习依赖
```bash
pip install scikit-learn>=1.3.0
pip install shap>=0.44.0
pip install statsmodels>=0.14.0
```

### 第6步: 安装数据库依赖
```bash
pip install SQLAlchemy>=2.0
pip install pymysql>=1.0.0
pip install psycopg2-binary>=2.9.0
```

### 第7步: 安装硬件和安全依赖
```bash
pip install pyserial>=3.5
pip install cryptography>=42.0
```

### 第8步: 安装打包工具
```bash
pip install nuitka>=4.0
```

### 第9步: 验证安装
```bash
pip list
python -c "import PySide6; import scipy; import pandas; import numpy; import matplotlib; print('所有核心依赖安装成功')"
```

### 第10步: 运行测试
```bash
cd D:\projects\QA-Tool
python -m pytest tests/ -v --tb=short
```

## 注意事项
1. **Python 3.14兼容性**: 部分包可能需要等待官方更新支持Python 3.14
2. **Windows特定依赖**: psycopg2-binary已包含Windows预编译版本
3. **GPU加速**: 如需GPU加速，可额外安装cupy等包
4. **开发依赖**: 如需开发工具，可额外安装pytest、ruff等

## 回滚计划
如安装失败，可使用以下命令回滚：
```bash
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```