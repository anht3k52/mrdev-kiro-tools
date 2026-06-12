==========================================================
 TOOL 3 — 9ROUTER INJECTOR (Fix loi 403)
==========================================================

CHUC NANG
  - Keo-tha (hoac chon) file JSON durable/cookie vao -> tool tu:
      1. Parse profileArn + token tu file
      2. Match dung connection Kiro trong 9router (theo IDC directory d-XXXX)
         - Co match  -> CAP NHAT profileArn (FIX 403)
         - Khong co  -> TAO MOI connection (khong can login truoc trong 9router)
      3. (tuy chon) Live verify goi API -> HTTP 200 la chac chan hien quota
      4. TU RESTART 9router (stop -> ghi DB -> start lai)
  - Bang trang thai cac connection: 🟢 OK / 403 (thieu profileArn) / ~1h (cookie-only).

YEU CAU
  - Windows + da cai 9router (chay 9router it nhat 1 lan de tao DB)
  - Python 3.10+ (tick "Add to PATH" khi cai Python)

CAI DAT (chi lan dau)
  - Bam dup  CAI_DAT.bat

CHAY
  - Bam dup  RUN.bat

CACH DUNG
  1. Keo-tha cac file JSON (xuat tu Tool 2, hoac cookie export) vao o xanh.
  2. Xem ban xem truoc (cap nhat / tao moi) -> bam Tiep tuc.
  3. Tool ghi DB + tu restart 9router. Doi vai giay -> quota hien len.

LOAI JSON DAU VAO
  - JSON durable (tu Tool 2): co refresh_token -> connection BEN, 9router tu refresh.
  - Cookie export (chi access + ProfileArn): chay duoc nhung CHET ~1h (phai inject
    trong vong 1 gio ke tu luc export).

LUU Y
  - Neu 403 quay lai sau 1 thoi gian (9router refresh lam mat profileArn) -> chi
    can keo file vao lai / bam Fix lai.

----------------------------------------------------------
 NGON NGU / LANGUAGE / 语言
----------------------------------------------------------
  Doi ngon ngu o goc tren ben phai: Tieng Viet / English / 中文
  (Change language at top-right dropdown.)
  README: README.txt (VI) | README.en.txt | README.zh.txt
  Tong hop: README.md | README.en.md | README.zh.md
