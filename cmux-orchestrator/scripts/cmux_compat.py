#!/usr/bin/env python3
"""cmux_compat.py — 크로스플랫폼 유틸리티 데먼

Unix 소켓 기반. macOS + Linux + WSL 호환.
grep -oP, date -j, stat -f 등 OS 종속 명령을 python3으로 통일.

사용법:
  python3 cmux_compat.py start   # 데먼 시작
  python3 cmux_compat.py stop    # 데먼 종료
  python3 cmux_compat.py status  # 상태 확인
  python3 cmux_compat.py --inline  # stdin에서 단일 요청 처리 (폴백용)
"""
import json
import os
import re
import signal
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from base64 import b64decode
from datetime import datetime, timezone
from pathlib import Path

SOCK_PATH = "/tmp/cmux-compat.sock"
PID_FILE = "/tmp/cmux-compat.pid"


# ─── 명령어 핸들러 ───

def cmd_json_get(args: dict) -> dict:
    """JSON 파일에서 키 값 추출. 중첩 키는 dot notation (a.b.c)"""
    fpath = args.get("file", "")
    key = args.get("key", "")
    try:
        with open(fpath) as f:
            data = json.load(f)
        parts = key.split(".") if key else []
        val = data
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            elif isinstance(val, list) and p.isdigit():
                val = val[int(p)]
            else:
                val = None
                break
        return {"ok": True, "value": val}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_json_set(args: dict) -> dict:
    """JSON 파일의 키에 값 설정 (원자적 쓰기)"""
    fpath = args.get("file", "")
    key = args.get("key", "")
    value = args.get("value")
    try:
        try:
            with open(fpath) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        parts = key.split(".")
        target = data
        for p in parts[:-1]:
            if p not in target or not isinstance(target[p], dict):
                target[p] = {}
            target = target[p]
        target[parts[-1]] = value
        tmp = fpath + ".tmp"
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.rename(tmp, fpath)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_json_query(args: dict) -> dict:
    """복합 JSON 쿼리. expr: 'keys', 'values', 'items', 'length', 'filter:key=val'"""
    fpath = args.get("file", "")
    expr = args.get("expr", "")
    try:
        with open(fpath) as f:
            data = json.load(f)
        if expr == "keys":
            return {"ok": True, "value": list(data.keys()) if isinstance(data, dict) else []}
        elif expr == "values":
            return {"ok": True, "value": list(data.values()) if isinstance(data, dict) else list(data)}
        elif expr == "items":
            return {"ok": True, "value": list(data.items()) if isinstance(data, dict) else []}
        elif expr == "length":
            return {"ok": True, "value": len(data)}
        elif expr.startswith("filter:"):
            # filter:status=IDLE → dict items where val.status == IDLE
            field, val = expr[7:].split("=", 1)
            result = {}
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict) and str(v.get(field, "")) == val:
                        result[k] = v
            return {"ok": True, "value": result}
        elif expr.startswith("map:"):
            # map:status → {k: v.status for k, v in data.items()}
            field = expr[4:]
            result = {}
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        result[k] = v.get(field)
            return {"ok": True, "value": result}
        else:
            return {"ok": False, "error": f"Unknown expr: {expr}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_epoch(args: dict) -> dict:
    """ISO 8601 타임스탬프 → epoch 초. 인자 없으면 현재 시간."""
    ts = args.get("timestamp", "")
    try:
        if not ts:
            return {"ok": True, "value": int(time.time())}
        # 여러 포맷 시도
        for fmt in [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
        ]:
            try:
                dt = datetime.strptime(ts, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return {"ok": True, "value": int(dt.timestamp())}
            except ValueError:
                continue
        return {"ok": False, "error": f"Unknown timestamp format: {ts}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_stat_mtime(args: dict) -> dict:
    """파일 수정 시간 (epoch 초)"""
    fpath = args.get("file", "")
    try:
        return {"ok": True, "value": int(os.path.getmtime(fpath))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_stat_size(args: dict) -> dict:
    """파일 크기 (bytes)"""
    fpath = args.get("file", "")
    try:
        return {"ok": True, "value": os.path.getsize(fpath)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_grep_pcre(args: dict) -> dict:
    """PCRE grep (grep -oP 대체). 매치된 그룹 또는 전체 매치 반환."""
    pattern = args.get("pattern", "")
    fpath = args.get("file", "")
    text = args.get("text", "")
    try:
        if fpath:
            with open(fpath) as f:
                text = f.read()
        matches = re.findall(pattern, text)
        return {"ok": True, "value": matches}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_readlink(args: dict) -> dict:
    """심링크 해석 (readlink -f 대체)"""
    fpath = args.get("file", "")
    try:
        return {"ok": True, "value": str(Path(fpath).resolve())}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_sed_inplace(args: dict) -> dict:
    """크로스플랫폼 sed -i"""
    fpath = args.get("file", "")
    pattern = args.get("pattern", "")
    replacement = args.get("replacement", "")
    try:
        with open(fpath) as f:
            content = f.read()
        new_content = re.sub(pattern, replacement, content)
        tmp = fpath + ".tmp"
        with open(tmp, "w") as f:
            f.write(new_content)
        os.rename(tmp, fpath)
        return {"ok": True, "value": content != new_content}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_base64_decode(args: dict) -> dict:
    """base64 디코딩"""
    data = args.get("data", "")
    try:
        return {"ok": True, "value": b64decode(data).decode("utf-8", errors="replace")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_mktemp(args: dict) -> dict:
    """크로스플랫폼 임시파일 생성"""
    prefix = args.get("prefix", "cmux-")
    suffix = args.get("suffix", "")
    try:
        fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
        os.close(fd)
        return {"ok": True, "value": path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def cmd_os_detect(_args: dict) -> dict:
    """OS/아키텍처 정보"""
    import platform
    uname = platform.uname()
    wsl = False
    try:
        with open("/proc/version") as f:
            if "microsoft" in f.read().lower():
                wsl = True
    except FileNotFoundError:
        pass
    return {
        "ok": True,
        "value": {
            "os": uname.system.lower(),
            "arch": uname.machine,
            "release": uname.release,
            "wsl": wsl,
            "python": platform.python_version(),
        },
    }


def cmd_version_check(args: dict) -> dict:
    """명령어 버전 확인"""
    cmd = args.get("command", "")
    try:
        result = subprocess.run(
            [cmd, "--version"],
            capture_output=True, text=True, timeout=5
        )
        output = (result.stdout or result.stderr).strip()
        # 첫 줄에서 버전 번호 추출
        version_match = re.search(r"(\d+\.\d+[\.\d]*)", output)
        return {
            "ok": True,
            "value": {
                "version": version_match.group(1) if version_match else output.split("\n")[0],
                "raw": output.split("\n")[0],
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── 명령어 디스패처 ───

COMMANDS = {
    "json-get": cmd_json_get,
    "json-set": cmd_json_set,
    "json-query": cmd_json_query,
    "epoch": cmd_epoch,
    "stat-mtime": cmd_stat_mtime,
    "stat-size": cmd_stat_size,
    "grep-pcre": cmd_grep_pcre,
    "readlink": cmd_readlink,
    "sed-inplace": cmd_sed_inplace,
    "base64-decode": cmd_base64_decode,
    "mktemp": cmd_mktemp,
    "os-detect": cmd_os_detect,
    "version-check": cmd_version_check,
    "ping": lambda _: {"ok": True, "value": "pong"},
}


def dispatch(request: dict) -> dict:
    cmd = request.get("cmd", "")
    args = request.get("args", {})
    handler = COMMANDS.get(cmd)
    if not handler:
        return {"ok": False, "error": f"Unknown command: {cmd}"}
    try:
        return handler(args)
    except Exception as e:
        return {"ok": False, "error": f"Internal error: {e}"}


# ─── 소켓 서버 ───

class RequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            for line in self.rfile:
                line = line.strip()
                if not line:
                    continue
                try:
                    request = json.loads(line)
                except json.JSONDecodeError:
                    response = {"ok": False, "error": "Invalid JSON"}
                else:
                    response = dispatch(request)
                self.wfile.write(json.dumps(response, ensure_ascii=False).encode() + b"\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass


class ThreadedUnixServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True


# ─── 데먼 관리 ───

def start_daemon():
    """데먼 시작 (포크)"""
    # 이미 실행 중인지 확인
    if os.path.exists(SOCK_PATH):
        try:
            s = socket.socket(socket.AF_UNIX)
            s.connect(SOCK_PATH)
            s.sendall(b'{"cmd":"ping"}\n')
            resp = s.makefile().readline()
            s.close()
            if "pong" in resp:
                print(f"cmux-compat daemon already running", file=sys.stderr)
                return
        except (ConnectionRefusedError, FileNotFoundError, OSError):
            os.unlink(SOCK_PATH)

    # 포크
    pid = os.fork()
    if pid > 0:
        # 부모: PID 기록 후 종료
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
        # 소켓 생성 대기 (최대 3초)
        for _ in range(30):
            if os.path.exists(SOCK_PATH):
                print(f"cmux-compat daemon started (pid={pid})", file=sys.stderr)
                return
            time.sleep(0.1)
        print(f"cmux-compat daemon forked (pid={pid}) but socket not ready", file=sys.stderr)
        return

    # 자식: 세션 리더로 분리
    os.setsid()
    # stdin/stdout/stderr 닫기
    sys.stdin.close()
    devnull = open(os.devnull, "w")
    sys.stdout = devnull
    sys.stderr = devnull

    # PID 갱신
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def cleanup(_signum, _frame):
        try:
            os.unlink(SOCK_PATH)
        except FileNotFoundError:
            pass
        try:
            os.unlink(PID_FILE)
        except FileNotFoundError:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGHUP, signal.SIG_IGN)

    try:
        server = ThreadedUnixServer(SOCK_PATH, RequestHandler)
        os.chmod(SOCK_PATH, 0o600)
        server.serve_forever()
    except Exception:
        cleanup(None, None)


def stop_daemon():
    """데먼 종료"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE) as f:
                pid = int(f.read().strip())
            os.kill(pid, signal.SIGTERM)
            # 종료 대기 (최대 3초)
            for _ in range(30):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.1)
                except ProcessLookupError:
                    break
            print(f"cmux-compat daemon stopped (pid={pid})", file=sys.stderr)
        except (ProcessLookupError, ValueError):
            print("cmux-compat daemon not running", file=sys.stderr)
        finally:
            for f in [PID_FILE, SOCK_PATH]:
                try:
                    os.unlink(f)
                except FileNotFoundError:
                    pass
    else:
        print("cmux-compat daemon not running (no PID file)", file=sys.stderr)
        if os.path.exists(SOCK_PATH):
            os.unlink(SOCK_PATH)


def status_daemon():
    """데먼 상태"""
    if not os.path.exists(SOCK_PATH):
        print("stopped")
        return
    try:
        s = socket.socket(socket.AF_UNIX)
        s.connect(SOCK_PATH)
        s.sendall(b'{"cmd":"ping"}\n')
        resp = s.makefile().readline()
        s.close()
        if "pong" in resp:
            pid = "?"
            if os.path.exists(PID_FILE):
                with open(PID_FILE) as f:
                    pid = f.read().strip()
            print(f"running (pid={pid})")
        else:
            print("error (socket exists but no response)")
    except (ConnectionRefusedError, FileNotFoundError, OSError):
        print("stale (socket exists but connection refused)")


def inline_mode():
    """stdin에서 단일 요청 처리 (데먼 없이 폴백용)"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "Invalid JSON"}))
            continue
        result = dispatch(request)
        print(json.dumps(result, ensure_ascii=False))
        sys.stdout.flush()


# ─── 메인 ───

def main():
    if len(sys.argv) < 2:
        print("Usage: cmux_compat.py {start|stop|status|--inline}", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "start":
        start_daemon()
    elif cmd == "stop":
        stop_daemon()
    elif cmd == "status":
        status_daemon()
    elif cmd == "--inline":
        inline_mode()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
