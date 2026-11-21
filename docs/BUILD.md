# 재빌드

## 준비물

- Python 3.11 이상
- `numpy`, `Pillow`, `opencv-python` (`pip install numpy pillow opencv-python`)
- Dolphin에 들어 있는 `DolphinTool.exe`
- 원본 일본판 GFZJ01 디스크(RVZ 또는 ISO)
  - ISO로 바꿨을 때 MD5가 `38249b82be648aaf08b42909064a957d`이어야 합니다.
- 글꼴(`docs/FONT_CREDITS.md`). `fonts/` 폴더에 둡니다.
- (배포 파일을 만들 때) xdelta3

## 순서

```powershell
python tools/prepare.py '.\F-Zero GX (Japan).rvz' 'C:\Dolphin\DolphinTool.exe'
```

이 명령이 하는 일은 다음과 같습니다.
1. 원본을 `orig.iso`로 변환하고 MD5를 확인합니다.
2. 디스크 파일을 `ext/`에 풉니다.
3. `enemy_line/line__.bin`을 복호화·압축 해제해 공용 실행 모듈 `fzmain.rel`을 만들고, 게임 글꼴의 글자표(`text/fontchars.txt`)를 꺼냅니다.
4. `text/index.json`(위치·칸 크기·길이만 담음)으로 원문 표 `text/strings_f.json`을 만듭니다.
5. `tools/dump_extra.py`로 인터뷰 대사·스토리 자막 원문(`text/jp/`)을 뽑습니다.

```powershell
python tools/build.py
```

- REL 문자열·인터뷰 대사·스토리 자막·일시정지 메뉴·이름 입력 표·글꼴·그림 글자를 바꾸고, 원본 ISO를 복사해 바뀐 파일을 다시 써 넣어 상위 폴더에 `F-Zero GX (Japan) [KOR].iso`를 만듭니다.
  - 출력 경로는 환경 변수 `OUT_ISO`로 바꿀 수 있습니다.
- 칸 크기를 넘는 문장이 있으면 `report.txt`에 `OVER`로 나옵니다. v1.1은 0건입니다.
- 텍스처 재압축 결과는 `tex/`에 캐시합니다. 처음 한 번은 몇 분 걸립니다.
- 결과 ISO의 MD5가 `README.md` 표의 값과 같으면 배포판과 같습니다.

## 배포 파일 만들기

```powershell
xdelta3 -e -0 -S none -A -s orig.iso '..\F-Zero GX (Japan) [KOR].iso' F-Zero_GX_GC_KO_v1.1.xdelta
```

## 테스트·분석 도구

- `tools/emu.py`, `tools/dsu.py`: Dolphin을 화면 밖에서 띄우고 가상 패드(DSU)로 조작해 화면을 캡처합니다. Dolphin 경로는 환경 변수 `DOLPHIN`으로 지정합니다.
- `tools/sheet.py`: `bmp/*.tpl.lz` 텍스처를 한 장의 PNG로 펼쳐 봅니다.
- `tools/extract.py`, `tools/ppcdis.py`: REL·DOL 문자열 추출과 코드 확인에 썼습니다.
