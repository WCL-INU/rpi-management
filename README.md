# Raspberry Pi Management Scripts

여러 Raspberry Pi 장비에 프로그램을 배포하고, 장비별 환경 파일을 작성하며, 원격에서 서비스를 활성화/업데이트하기 위한 관리 스크립트 모음입니다.

이 저장소는 각 프로그램의 애플리케이션 로직을 관리하는 곳이 아닙니다. `data/<program>/` 아래에 놓인 프로그램 디렉터리는 배포 대상 소스이며, 이 프로젝트의 관심사는 해당 디렉터리를 여러 Raspberry Pi에 안전하고 반복 가능하게 복사하고 실행 환경을 맞추는 것입니다.

## 준비 사항

- Python 3.10 이상
- [uv](https://github.com/astral-sh/uv)
- 각 Raspberry Pi에 SSH 접속 가능해야 함
- 로컬에서 `ssh <host>`가 비밀번호 입력 없이 동작하는 상태 권장
- 원격 Raspberry Pi의 기본 배포 경로는 `/home/pi/wcl/`

의존성 설치:

```bash
uv sync
```

## 디렉터리 구성

```text
.
├── README.md
├── docs/
│   └── web-management-scope.md
├── main.py
├── pyproject.toml
├── data/
│   ├── devices.yaml
│   ├── list-of-programs
│   └── <program>/
│       ├── setup
│       └── env/
│           └── .env.example
└── src/
    ├── copy-programs.py
    ├── enable-programs.py
    ├── run-python-script.py
    ├── run-script.py
    ├── update-programs.py
    ├── web.py
    ├── write-env-file.py
    └── utils/
        └── devices_config.py
└── web/
    ├── app.js
    ├── index.html
    └── styles.css
```

`data/`는 운영 설정과 배포 대상 파일을 두는 작업 디렉터리입니다. 장비 접속 정보, 환경 변수, 수집 결과 등이 들어가므로 Git에 올리지 않습니다.

## 장비 설정

장비 목록은 `data/devices.yaml`에 작성합니다.

```yaml
devices:
  - id: raspberrypi-1
    host: raspberrypi-1.local
    env:
      SERVER_URL: "https://example.com/api/upload"
      HIVE_ID: 44
      SENSOR_TYPE_ID: 2
      SENSOR_DEVICE_IDs: "134 135 136"
    programs:
      - sensor-uploader

  - id: raspberrypi-2
    host: raspberrypi-2.local
    env:
      SERVER_URL: "https://example.com/api/upload"
      HIVE_ID: 45
      SENSOR_TYPE_ID: 2
      SENSOR_DEVICE_IDs: "137 138 139"
```

필드 설명:

| 필드 | 설명 |
| --- | --- |
| `id` | 장비 식별자입니다. 결과 수집 디렉터리 이름으로도 사용됩니다. |
| `host` | SSH 접속 대상입니다. 생략하면 `id`를 host로 사용합니다. |
| `env` | 장비별 환경 변수 값입니다. |
| `programs` | 해당 장비에 배포할 프로그램 목록입니다. 생략하면 `data/list-of-programs`를 사용합니다. |

공통 프로그램 목록은 `data/list-of-programs`에 한 줄에 하나씩 작성합니다.

```text
sensor-uploader
camera-client
```

## 프로그램 디렉터리 준비

배포할 프로그램은 `data/<program>/` 아래에 둡니다.

예시:

```text
data/
└── sensor-uploader/
    ├── setup
    ├── requirements.txt
    ├── upload-sensor.service
    ├── env/
    │   └── .env.example
    └── src/
        └── upload.py
```

`setup` 파일은 원격 Raspberry Pi에서 실행됩니다. 보통 가상환경 생성, 의존성 설치, systemd 서비스 등록 같은 작업을 넣습니다.

```bash
#!/bin/bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo cp upload-sensor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable upload-sensor.service
sudo systemctl start upload-sensor.service
```

환경 파일 템플릿은 `data/<program>/env/.env.example`에 작성합니다. `write-env-file.py`는 이 파일에서 필요한 키를 읽고, 각 장비의 `env` 값으로 원격 `.env` 파일을 생성합니다.

```text
SERVER_URL=<server url>
HIVE_ID=<device group id>
SENSOR_TYPE_ID=<sensor type id>
SENSOR_DEVICE_IDs=<space separated sensor ids>
```

## 기본 사용 흐름

### 1. 프로그램 복사

`data/<program>/` 디렉터리를 각 Raspberry Pi의 `/home/pi/wcl/<program>/`로 복사합니다.

```bash
uv run src/copy-programs.py
```

또는:

```bash
uv run main.py copy-programs
```

### 2. 장비별 `.env` 작성

`devices.yaml`과 각 프로그램의 `.env.example`을 기준으로 원격 `.env` 파일을 작성합니다.

```bash
uv run src/write-env-file.py
```

또는:

```bash
uv run main.py write-env-file
```

생성 위치:

```text
/home/pi/wcl/<program>/env/.env
```

### 3. 프로그램 활성화

각 Raspberry Pi에서 `/home/pi/wcl/<program>/setup`을 실행합니다.

```bash
uv run src/enable-programs.py
```

또는:

```bash
uv run main.py enable-programs
```

### 4. 프로그램 업데이트

기존 systemd 서비스를 중지하고, 프로그램 파일을 다시 복사한 뒤 서비스를 재시작합니다.

```bash
uv run src/update-programs.py
```

또는:

```bash
uv run main.py update-programs
```

`update-programs.py`는 `.git`과 `.env`를 제외하고 rsync합니다. 따라서 원격 장비의 환경 파일은 업데이트 중 보존됩니다.

서비스 이름은 다음 규칙을 사용합니다.

```text
upload-<program>
```

예를 들어 프로그램 이름이 `sensor-uploader`이면 중지/시작 대상은 `upload-sensor-uploader`입니다.

## 웹 관리 페이지

등록된 Raspberry Pi 장비가 현재 동작 중인지와 기본 상태를 읽기 전용 대시보드로 확인할 수 있습니다. 메인 화면에는 uptime, RAM, storage, CPU 활성 상태, network 상태, CPU 온도, camera 상태를 표시하고, 프로그램 목록, 환경 변수 키, CLI 명령 안내 같은 설정 정보는 표시하지 않습니다.

```bash
uv run main.py web
```

브라우저에서 다음 주소를 엽니다.

```text
http://127.0.0.1:8080
```

기능 범위와 제외 항목은 `docs/web-management-scope.md`에 정리되어 있습니다.
## 원격 스크립트 실행 및 결과 수집

관리 중인 장비에서 임시 진단 스크립트를 실행하고 결과 파일을 가져올 수 있습니다.

### Shell 스크립트 실행

로컬의 `data/script.sh`를 각 장비의 `/tmp/run-script.sh`로 복사한 뒤 실행합니다.

```bash
uv run src/run-script.py
```

원격 스크립트는 `/tmp/script_outputs.json` 파일을 만들어야 합니다.

```json
{
  "files": [
    "/tmp/script_output.txt"
  ]
}
```

수집된 파일은 장비별 디렉터리에 저장됩니다.

```text
data/<device-id>/<filename>
```

### Python 스크립트 실행

로컬의 `data/script.py`를 각 장비의 `/tmp/run-script.py`로 복사한 뒤 `python3`로 실행합니다.

```bash
uv run src/run-python-script.py
```

이 스크립트도 원격에서 `/tmp/script_outputs.json`을 생성해야 합니다. 수집된 파일은 `data/images/`에 저장됩니다.

## 설정 파일을 코드에서 다루기

`src/utils/devices_config.py`는 `devices.yaml`을 읽고 쓰기 위한 헬퍼를 제공합니다.

```python
from utils.devices_config import load_devices, save_devices, upsert_device

devices = load_devices()
upsert_device(
    devices,
    "raspberrypi-1",
    host="raspberrypi-1.local",
    env={"SERVER_URL": "https://example.com/api/upload"},
    programs=["sensor-uploader"],
)
save_devices(devices)
```

주요 함수:

| 함수 | 설명 |
| --- | --- |
| `load_devices()` | `data/devices.yaml`에서 장비 목록을 읽습니다. |
| `save_devices(devices)` | 장비 목록을 `data/devices.yaml`에 저장합니다. |
| `get_device(devices, device_id)` | ID로 장비를 찾습니다. |
| `upsert_device(...)` | 장비를 추가하거나 기존 장비를 갱신합니다. |
| `update_device_env(device, updates)` | 장비의 `env` 값을 병합합니다. |
| `set_device_programs(device, programs)` | 장비의 프로그램 목록을 교체합니다. |
| `load_programs_list()` | `data/list-of-programs`를 읽습니다. |

## 운영 팁

- `devices.yaml`에는 서버 URL, 장비 ID, 센서 ID 등 운영 값이 들어갈 수 있으므로 공개 저장소에 커밋하지 않습니다.
- 새 프로그램을 추가할 때는 먼저 `data/<program>/env/.env.example`의 키와 `devices.yaml`의 `env` 키가 일치하는지 확인합니다.
- 장비별로 프로그램 구성이 다르면 `devices.yaml`의 `programs`를 명시하고, 모든 장비가 같은 프로그램을 쓰면 `data/list-of-programs`를 사용합니다.
- `setup`은 원격 장비에서 실행되므로 반복 실행해도 문제가 없도록 작성하는 것이 좋습니다.
- 업데이트 전에는 systemd 서비스 이름이 `upload-<program>` 규칙과 일치하는지 확인합니다.
- 원격 진단 스크립트는 수집할 파일 목록을 `/tmp/script_outputs.json`에 반드시 기록해야 합니다.

## 문제 해결

### 장비가 건너뛰어짐

`devices.yaml`에 `id` 또는 `host`가 없으면 해당 장비는 건너뜁니다.

### 프로그램이 건너뛰어짐

장비에 `programs`가 없고 `data/list-of-programs`도 비어 있으면 배포할 프로그램이 없어 건너뜁니다.

### `.env`가 생성되지 않음

다음을 확인합니다.

- `data/<program>/env/.env.example` 파일이 있는지
- `.env.example`에 `KEY=value` 형식의 줄이 있는지
- `devices.yaml`의 `env`에 해당 키가 있는지

### 원격 결과 파일이 수집되지 않음

`run-script.py` 또는 `run-python-script.py`를 사용할 때 원격 스크립트가 `/tmp/script_outputs.json`을 생성했는지 확인합니다. `files` 값은 문자열 또는 파일 경로 배열이어야 합니다.
