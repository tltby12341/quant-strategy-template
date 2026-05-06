import requests
import json
import time
import hashlib
import base64
import logging
from .config import get_credentials

logger = logging.getLogger("qc_api")

# 重试配置
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # 指数退避基数（秒）
RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429}


class QCApiClient:
    def __init__(self):
        self.user_id, self.api_token = get_credentials()
        self.base_url = "https://www.quantconnect.com/api/v2"

    def _request(self, method, endpoint, data=None):
        url = f"{self.base_url}/{endpoint}"

        last_exception = None
        for attempt in range(MAX_RETRIES):
            ts = str(int(time.time()))
            token_hash = hashlib.sha256(
                f"{self.api_token}:{ts}".encode('utf-8')
            ).hexdigest()
            auth_str = f"{self.user_id}:{token_hash}"
            base64_auth = base64.b64encode(auth_str.encode('ascii')).decode('ascii')

            headers = {
                "Accept": "application/json",
                "Timestamp": ts,
                "Authorization": f"Basic {base64_auth}",
            }

            try:
                if method.lower() == 'get':
                    response = requests.get(url, params=data, headers=headers, timeout=30)
                elif method.lower() == 'post':
                    response = requests.post(url, data=data, headers=headers, timeout=60)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                # 可重试的 HTTP 状态码
                if response.status_code in RETRYABLE_STATUS_CODES:
                    wait = RETRY_BACKOFF_BASE ** attempt
                    logger.warning(
                        f"API {endpoint} 返回 {response.status_code}，"
                        f"{wait}s 后重试 ({attempt + 1}/{MAX_RETRIES})"
                    )
                    time.sleep(wait)
                    last_exception = requests.exceptions.HTTPError(
                        f"{response.status_code}: {response.text[:200]}"
                    )
                    continue

                if response.status_code != 200:
                    logger.error(f"API Error {response.status_code}: {response.text[:300]}")

                response.raise_for_status()
                return response.json()

            except requests.exceptions.ConnectionError as e:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"API {endpoint} 连接失败，{wait}s 后重试 ({attempt + 1}/{MAX_RETRIES}): {e}"
                )
                time.sleep(wait)
                last_exception = e
            except requests.exceptions.Timeout as e:
                wait = RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    f"API {endpoint} 超时，{wait}s 后重试 ({attempt + 1}/{MAX_RETRIES}): {e}"
                )
                time.sleep(wait)
                last_exception = e
            except requests.exceptions.RequestException as e:
                # 非可重试错误（4xx 等），直接抛出
                logger.error(f"API Request Error ({endpoint}): {e}")
                raise

        # 重试耗尽
        logger.error(f"API {endpoint} 重试 {MAX_RETRIES} 次后仍然失败")
        raise last_exception or RuntimeError(f"API {endpoint} failed after {MAX_RETRIES} retries")

    def read_project(self, project_id):
        """test connection by reading project"""
        # GET /projects/read
        return self._request('get', 'projects/read', data={'projectId': project_id})

    def create_file(self, project_id, file_name, content):
        """Create a new file in the project."""
        return self._request('post', 'files/create', data={
            'projectId': project_id,
            'name': file_name,
            'content': content,
        })

    def update_project_files(self, project_id, files_list):
        """
        Update text files in a project (create if not exists).
        files_list: list of {'name': 'main.py', 'content': '...'}
        QC API requires one request per file with individual name/content fields.
        """
        results = []
        for f in files_list:
            payload = {
                'projectId': project_id,
                'name': f['name'],
                'content': f['content'],
            }
            result = self._request('post', 'files/update', data=payload)
            if not result.get('success'):
                errors = result.get('errors', [])
                # File doesn't exist yet — create it
                if any('not found' in str(e).lower() for e in errors):
                    logger.info(f"File {f['name']} not found, creating...")
                    result = self.create_file(project_id, f['name'], f['content'])
                    if not result.get('success'):
                        raise RuntimeError(f"Failed to create {f['name']}: {result.get('errors')}")
                else:
                    raise RuntimeError(f"Failed to update {f['name']}: {errors}")
            results.append(result)
        return results

    def delete_file(self, project_id, file_name):
        """Delete a file from the project"""
        # POST /files/delete
        return self._request('post', 'files/delete', data={
            'projectId': project_id,
            'name': file_name
        })

    def create_compile(self, project_id):
        """Trigger a compilation"""
        # POST /compile/create
        return self._request('post', 'compile/create', data={'projectId': project_id})

    def read_compile(self, project_id, compile_id):
        """Check compilation status"""
        # GET /compile/read
        return self._request('get', 'compile/read', data={'projectId': project_id, 'compileId': compile_id})

    def create_backtest(self, project_id, compile_id, backtest_name):
        """Trigger a backtest"""
        # POST /backtests/create
        return self._request('post', 'backtests/create', data={
            'projectId': project_id,
            'compileId': compile_id,
            'backtestName': backtest_name
        })

    def read_backtest(self, project_id, backtest_id):
        """Check backtest status and get results"""
        # GET /backtests/read
        return self._request('get', 'backtests/read', data={
            'projectId': project_id,
            'backtestId': backtest_id
        })

    def read_backtest_orders(self, project_id, backtest_id, start=0, end=100):
        """Read orders from a completed backtest"""
        # GET /backtests/orders/read
        return self._request('get', 'backtests/orders/read', data={
            'projectId': project_id,
            'backtestId': backtest_id,
            'start': start,
            'end': end,
        })

    def read_backtest_trades(self, project_id, backtest_id, start=0, end=100):
        """Read closed trades (round-trips) from a completed backtest"""
        return self._request('get', 'backtests/trades/read', data={
            'projectId': project_id,
            'backtestId': backtest_id,
            'start': start,
            'end': end,
        })

    def read_backtest_logs(self, project_id, backtest_id, start=0, end=200, query=''):
        """Read log lines from a completed backtest (max 200 per page)"""
        return self._request('get', 'backtests/read/log', data={
            'projectId': project_id,
            'backtestId': backtest_id,
            'start': start,
            'end': end,
            'query': query,
        })

    def list_backtests(self, project_id):
        """List all backtests for a project"""
        # GET /backtests/read (no backtestId returns list)
        return self._request('get', 'backtests/read', data={'projectId': project_id})

    def delete_backtest(self, project_id, backtest_id):
        """Delete (abort) a running or completed backtest. Does NOT delete the project."""
        # POST /backtests/delete
        return self._request('post', 'backtests/delete', data={
            'projectId': project_id,
            'backtestId': backtest_id,
        })


