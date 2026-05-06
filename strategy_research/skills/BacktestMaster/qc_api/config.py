import os
import re

def _load_dotenv():
    """从项目根目录的 .env 文件加载环境变量（不覆盖已有的）"""
    # 从当前文件向上查找 .env
    search_dir = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):  # 最多向上找 6 层
        env_path = os.path.join(search_dir, ".env")
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue
                    key, _, value = line.partition('=')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
            return
        parent = os.path.dirname(search_dir)
        if parent == search_dir:
            break
        search_dir = parent

def get_credentials():
    """
    读取 QuantConnect API 凭证。
    优先级: 环境变量 > 项目 .env 文件 > ~/.lean/credentials 文件
    """
    # 0. 尝试从 .env 文件加载
    _load_dotenv()

    # 1. 环境变量（含 .env 加载的）
    user_id = os.environ.get("QC_USER_ID")
    api_token = os.environ.get("QC_API_TOKEN")
    if user_id and api_token:
        return user_id, api_token

    # 2. ~/.lean/credentials 文件 fallback
    lean_cred_path = os.path.expanduser("~/.lean/credentials")
    if os.path.exists(lean_cred_path):
        try:
            with open(lean_cred_path) as f:
                content = f.read()
            uid_match = re.search(r'user-id\s*=\s*(\S+)', content)
            token_match = re.search(r'api-token\s*=\s*(\S+)', content)
            if uid_match and token_match:
                return uid_match.group(1), token_match.group(1)
        except Exception:
            pass

    raise ValueError(
        "QuantConnect 凭证未配置。请设置环境变量:\n"
        "  export QC_USER_ID=your_user_id\n"
        "  export QC_API_TOKEN=your_api_token\n"
        "或在 ~/.lean/credentials 中配置 user-id 和 api-token"
    )

def get_default_project_id():
    """
    Returns the default project ID for this skill set.
    """
    _load_dotenv()
    project_id = os.environ.get("QC_PROJECT_ID")
    if not project_id:
        raise ValueError(
            "QC_PROJECT_ID 未配置。请在项目根目录 .env 文件或环境变量中设置:\n"
            "  QC_PROJECT_ID=<your_project_id>"
        )
    return int(project_id)
