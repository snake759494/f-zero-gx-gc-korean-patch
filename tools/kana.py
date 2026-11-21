"""Name-entry grids: replace hiragana/katakana sets with Korean syllables; blank dakuten tables."""
import re
A = ('가나다라마바사아자차카타파하거너더러머버서어저처커터퍼허고노도로모보소오조초코토포호'
     '구누두루무부수우주추쿠투푸후그느드르므브스으즈츠크트프흐기니디리미비시이지치키티피히'
     '개내대래매배새애재채해')
B = ('강건경곤공관광국권규근금길김남덕동란람랑련령룡류륜린림만명문민박백범별봉빈상석선'
     '설성세솔송숙순승신실심안양연영옥완용운원윤은을인일임장전정제종준중진창철청최춘태'
     '택한혁현형홍화환황효훈희')
assert len(set(A)) == len(A) >= 85 and len(set(B)) == len(B) >= 88 and not set(A) & set(B)
KANA = lambda c: 0x3041 <= ord(c) <= 0x30f6 and c != 'ー'
def patch(data):
    data = bytearray(data); n = 0
    for m in re.finditer(rb'[^\x00]{120,}', bytes(data)):
        try: s = m.group().decode('cp932')
        except UnicodeDecodeError: continue
        k = sum(map(KANA, s))
        if k < 18 or k + s.count('　') + s.count('∫') + s.count('∬') != len(s): continue
        if s[0] == chr(0x3042): src = iter(A)
        elif s[0] == chr(0x30a2): src = iter(B)
        else: src = None
        t = ''.join((next(src) if src else '　') if KANA(c) else c for c in s)
        yield m.start(), t; n += 1
