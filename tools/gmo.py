"""game/ja.gmo (gettext catalog, translations by entry index) + game/game_msg_jp.txt (by line)"""
import struct
GMO = ['티켓을\n%d장\n얻었습니다', '괜찮습니까？', '빅 블루', '계속하기', '코스 선택', '그만두기', '그랑프리를 종료합니다', '레이스를 종료합니다', '이 시나리오를 종료합니다', '리플레이를 종료합니다', '타임 어택을 종료합니다', '강제 승리', '다음으로', '고스트 저장', '세팅으로 들어갑니다', '미션 표시', '뮤트 시티', '아니요', '추가 BGM\n/bc00ffff/%s/bcffffff/\n이(가) 입고되었습니다\n숍에서 구입할 수 있습니다', '스토리 모드\n/bc00ffff/%s/bcffffff/\n이(가) 입고되었습니다\n숍에서 구입할 수 있습니다', '아케이드 코스\n/bc00ffff/%s/bcffffff/\n이(가) 입고되었습니다\n숍에서 구입할 수 있습니다', '새로운 머신\n/bc00ffff/%s/bcffffff/\n이(가) 입고되었습니다\n숍에서 구입할 수 있습니다', '새로운 파츠\n/bc00ffff/%s/bcffffff/\n이(가) 입고되었습니다\n숍에서 구입할 수 있습니다', '스태프 고스트\n/bc00ffff/%s/bcffffff/\n이(가) 입고되었습니다\n숍에서 구입할 수 있습니다', '리플레이', '리플레이 저장', '재시작', '재도전', '레이스를 다시 합니다', '세팅', '상태', '코스를 다시 선택합니다', '재시작합니다', '이 레이스에서는\n고스트를 저장할 수 없습니다', '이 레이스에서는\n리플레이를 저장할 수 없습니다', '이 레이스에서는 리플레이와\n고스트 모두 저장할 수 없습니다', '예']
MSG = ['랭킹', '포인트', '주행 중', '코스', '시점', '결과', '리셋', '(예정)', '순위', '토탈', '베스트 랩', 'A 또는 메뉴를 눌러 주세요', '최고 속도', '랩', '골', '리플레이', '재도전', '실격', '예', '아니요', '예', '종료', '취소', '다음 스테이지', '재도전', '리플레이', '고스트', '저장', '로드', '상태', '편집', '파괴', '차', '세팅', '강제', '승리']
def texts(): return GMO + [x for x in MSG if x]
def build(enc, report):
    out = {}
    d = open('ext/files/game/ja.gmo', 'rb').read()
    mg, rev, n, ko, to, hs, ho = struct.unpack('<7I', d[:28])
    assert n == len(GMO)
    tr = [struct.unpack('<2I', d[to + 8 * i:to + 8 * i + 8]) for i in range(n)]
    start = min(o for l, o in tr)
    body = bytearray(d[:start]); new = []
    for i in range(n):
        b = enc.enc(GMO[i]); new.append((len(b), len(body))); body += b + bytes(1)
    for i, (l, o) in enumerate(new): struct.pack_into('<2I', body, to + 8 * i, l, o)
    out['game/ja.gmo'] = bytes(body)
    t = open('ext/files/game/game_msg_jp.txt', 'rb').read().decode('cp932')
    nl = chr(13) + chr(10) if chr(13) in t else chr(10); res = []; k = 0
    for ln in t.split(nl):
        if ':' in ln:
            key = ln.split(':', 1)[0]; v = MSG[k]; k += 1
            if v: res.append(key.encode('cp932') + b':' + enc.enc(v)); continue
        res.append(ln.encode('cp932'))
    out['game/game_msg_jp.txt'] = nl.encode().join(res)
    return out
