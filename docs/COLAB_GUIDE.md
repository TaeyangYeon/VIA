# Google Colab 연결 가이드

VIA는 로컬 Ollama 대신 **Google Colab GPU**에서 실행 중인 Ollama 서버에 연결할 수 있습니다.  
Intel Mac에서 Gemma4 추론이 느릴 때 Colab GPU(T4/A100)를 활용하면 속도를 크게 향상시킬 수 있습니다.

---

## 목차

- [Colab 연결이 필요한 경우](#colab-연결이-필요한-경우)
- [모델 선택](#모델-선택)
- [Colab 서버 설정 단계](#colab-서버-설정-단계)
- [VIA에서 Colab 연결하기](#via에서-colab-연결하기)
- [워밍업 절차 (필수)](#워밍업-절차-필수)
- [문제 해결](#문제-해결)

---

## Colab 연결이 필요한 경우

다음 상황에서 Colab 연결을 권장합니다:

- **Intel Mac에서 추론 속도 느림**: gemma4:e4b 첫 멀티모달 호출 시 2분 30초 이상 소요
- **더 높은 품질의 결과 필요**: gemma4:27b (27B 파라미터) 사용 시
- **반복 테스트**: 여러 번 파이프라인을 실행해야 할 때 GPU가 훨씬 빠름
- **로컬 메모리 부족**: gemma4:e4b는 약 4-5GB RAM 필요

**로컬 실행으로 충분한 경우:**
- 간헐적인 단일 실행
- Apple Silicon (M1/M2/M3) Mac (추론 속도 양호)
- 오프라인 환경

---

## 모델 선택

| 모델 | 파라미터 | 특징 | Colab GPU |
|------|---------|------|-----------|
| `gemma4:e4b` | ~4B (MoE) | 기본값, 빠름, 가벼움 | T4 이상 |
| `gemma4:27b` | 27B | 더 높은 품질, 느림 | A100 권장 |

> VIA 기본값은 `gemma4:e4b`입니다. 품질이 중요한 경우 `gemma4:27b`를 선택하세요.  
> `gemma4:27b`는 A100 GPU에서도 Pull에 약 15-20분 소요됩니다.

---

## Colab 서버 설정 단계

### 1단계: 셋업 노트북 다운로드

VIA에서 Colab 셋업 노트북을 다운로드합니다.

**앱에서 다운로드:**
1. Engine Settings 패널 열기
2. "Colab 모드" 선택
3. "Colab 셋업 노트북 다운로드" 버튼 클릭
4. `via_colab_setup.ipynb` 파일 저장

**API로 다운로드:**
```bash
curl http://localhost:8000/api/colab/notebook -o via_colab_setup.ipynb
```

### 2단계: Google Colab에서 열기

1. [colab.research.google.com](https://colab.research.google.com) 접속
2. 파일 → 노트북 업로드 → `via_colab_setup.ipynb` 선택

### 3단계: GPU 런타임 설정

1. 런타임 → 런타임 유형 변경
2. 하드웨어 가속기: **T4 GPU** 선택 (무료 티어)
3. 저장

> 무료 Colab은 T4 GPU가 제공됩니다. 더 빠른 속도가 필요하면 Colab Pro (A100)를 사용하세요.

### 4단계: 셀 실행

노트북에는 다음 셀이 포함되어 있습니다:

**셀 1: Ollama 설치 및 시작**
```bash
# Ollama 설치
curl -fsSL https://ollama.com/install.sh | sh

# 백그라운드에서 시작
!nohup ollama serve &
import time; time.sleep(3)
```

**셀 2: 모델 Pull**
```bash
# gemma4:e4b Pull (약 3.3GB)
!ollama pull gemma4:e4b

# 또는 27B 모델
# !ollama pull gemma4:27b
```

**셀 3: cloudflared 터널 시작**
```bash
# cloudflared 설치
!wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
!chmod +x cloudflared

# 터널 시작 (공개 URL 생성)
import subprocess, threading, re, time

proc = subprocess.Popen(
    ['./cloudflared', 'tunnel', '--url', 'http://localhost:11434'],
    stderr=subprocess.PIPE, text=True
)

# URL 추출
for line in proc.stderr:
    m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
    if m:
        print(f"\n✅ 터널 URL: {m.group()}\n")
        print("이 URL을 VIA Engine Settings에 입력하세요.")
        break
```

**셀 4: 연결 테스트**
```bash
# Ollama API 응답 확인
!curl http://localhost:11434/api/tags
```

모든 셀을 순서대로 실행하면 터널 URL이 출력됩니다:

```
✅ 터널 URL: https://abc123def456.trycloudflare.com

이 URL을 VIA Engine Settings에 입력하세요.
```

### 5단계: 터널 URL 복사

출력된 `https://xxxxxx.trycloudflare.com` URL을 복사합니다.

---

## VIA에서 Colab 연결하기

### 앱 UI에서 연결

1. VIA 앱의 **Engine Settings 패널** 열기
2. 엔진 모드: **Colab** 선택
3. Colab URL 입력 창에 복사한 URL 붙여넣기  
   예: `https://abc123def456.trycloudflare.com`
4. **연결 테스트** 버튼 클릭
5. "연결 성공" 메시지 확인

### API로 설정 (개발/테스트 시)

```bash
# Colab 모드로 전환
curl -X POST http://localhost:8000/api/engine/config \
  -H "Content-Type: application/json" \
  -d '{"mode": "colab", "colab_url": "https://abc123def456.trycloudflare.com"}'

# 현재 엔진 상태 확인
curl http://localhost:8000/api/engine/status
```

---

## 워밍업 절차 (필수)

> **⚠️ 중요**: Colab 연결 후 **첫 번째 Gemma4 요청은 반드시 실패합니다.**

**원인**: Ollama가 첫 요청 시 모델을 메모리에 로딩합니다. 이 과정이 30~90초 걸리며, 해당 시간 동안 타임아웃이 발생합니다.

**해결**: 파이프라인 실행 전에 반드시 **워밍업 요청**을 먼저 보내세요.

### 워밍업 방법

**방법 1: 앱 UI에서 (권장)**

Engine Settings 패널의 "연결 테스트" 버튼이 간단한 텍스트 요청을 보냅니다. 연결 테스트 성공 후 30초 기다렸다가 파이프라인을 실행하세요.

**방법 2: curl로 워밍업**

```bash
# 간단한 텍스트 요청으로 모델 로딩 유도
curl -X POST https://abc123def456.trycloudflare.com/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "gemma4:e4b", "prompt": "Say OK", "stream": false}' \
  --max-time 120

# 응답이 오면 모델이 메모리에 로딩된 것입니다
# 이후 VIA 파이프라인 실행 가능
```

**방법 3: E2E 테스트에서 워밍업**

```bash
# 환경 변수 설정 후 워밍업 스크립트 실행
VIA_OLLAMA_URL=https://abc123def456.trycloudflare.com python -c "
import httpx, asyncio
async def warmup():
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post(
            'https://abc123def456.trycloudflare.com/api/generate',
            json={'model': 'gemma4:e4b', 'prompt': 'Say OK', 'stream': False}
        )
        print('워밍업 완료:', r.status_code)
asyncio.run(warmup())
"
```

### 워밍업 완료 확인

워밍업이 완료되면 이후 요청은 빠르게 응답합니다 (T4 GPU 기준 10~30초).

---

## 문제 해결

### 터널 URL 만료

**증상**: 연결 테스트 실패, `connection refused` 오류  
**원인**: cloudflared 터널 URL은 Colab 세션이 살아있는 동안만 유효합니다. 세션 종료 또는 재시작 시 새 URL이 생성됩니다.  
**해결**:
1. Colab 노트북에서 셀 3을 다시 실행하여 새 URL 생성
2. VIA Engine Settings에서 새 URL로 업데이트

---

### 모델 Pull 실패

**증상**: `pull model manifest: file does not exist` 오류  
**원인**: Colab에서 Ollama가 모델을 다운로드하지 못함 (네트워크 문제 또는 디스크 부족)  
**해결**:

```bash
# Colab에서 디스크 공간 확인
!df -h /root

# 모델 다시 Pull
!ollama pull gemma4:e4b

# Ollama 상태 확인
!ollama list
```

---

### 콜드 스타트 후 첫 번째 요청 실패

**증상**: 파이프라인 실행 시 `ReadTimeout` 또는 `502 Bad Gateway`  
**원인**: 모델이 아직 로딩 중  
**해결**: [워밍업 절차](#워밍업-절차-필수) 섹션을 참고하여 워밍업 후 재시도

---

### gemma4:27b 모델 응답 매우 느림

**증상**: 에이전트 실행에 5분 이상 소요  
**원인**: T4 GPU는 27B 모델에 부족  
**해결**: Colab Pro 구독 후 A100 GPU 런타임 선택, 또는 `gemma4:e4b`로 전환

---

### Colab 세션 자동 종료

**증상**: 연결이 갑자기 끊김  
**원인**: Google Colab은 90분 이상 유휴 상태면 세션을 종료합니다.  
**해결**:
- 긴 작업 전 Colab 탭을 유지
- 세션 종료 시 노트북 재실행 후 새 URL로 재연결

---

### VIA_OLLAMA_URL 환경 변수로 E2E 테스트 실행

```bash
# E2E 통합 테스트 (실제 Gemma4 필요)
VIA_OLLAMA_URL=https://abc123def456.trycloudflare.com \
  python -m pytest tests/e2e/test_final_integration.py \
  -m "integration and e2e" -v

# 워밍업 후 실행 권장
# Scenario 1/2에서 test_results=[] 는 정상 동작 (Gemma4 코드 생성 비결정성)
```
