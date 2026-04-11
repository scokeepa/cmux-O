"""conftest.py — pytest 최초 로드 시 ChromaDB 환경 설정.

ChromaDB 0.6.x의 ONNX Runtime CoreML provider segfault를 방지하고,
posthog telemetry 경고를 억제한다.

근거: mempalace/tests/conftest.py + mempalace/__init__.py 패턴.
"""

import logging
import os

# ONNX Runtime CoreML provider segfault 방지 (Apple Silicon)
# 프로덕션 코드는 각 모듈에서 _cpu_embedding()으로 preferred_providers=["CPUExecutionProvider"]를
# 명시하지만, 테스트가 직접 chromadb를 import하는 경로를 위해 환경변수도 설정.
os.environ["ORT_DISABLE_COREML"] = "1"

# ChromaDB posthog telemetry 비활성화
os.environ["ANONYMIZED_TELEMETRY"] = "False"

# posthog capture() signature 불일치 경고 억제
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
